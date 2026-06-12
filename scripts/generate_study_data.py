import csv
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.database import Base, SessionLocal, engine  # noqa: E402
from backend.app.models import (  # noqa: E402
    Exercise,
    Objective,
    Profile,
    Routine,
    RoutineExercise,
    User,
    WorkoutLog,
    WorkoutLogExercise,
)
from backend.app.recommender import build_routine, calories_from_met  # noqa: E402
from scripts.import_survey_users import ensure_objectives, import_row, read_rows  # noqa: E402


# Marca usada para diferenciar datos sinteticos de estudio frente a datos
# creados manualmente desde la interfaz.
SOURCE = "survey_eda_v1"
REPORT_PATH = ROOT_DIR / "data" / "processed" / "study_generation_report.md"
SUMMARY_PATH = ROOT_DIR / "data" / "processed" / "study_activity_summary.csv"


def main() -> None:
    Base.metadata.create_all(bind=engine)
    rows = read_rows()

    with SessionLocal() as db:
        ensure_objectives(db)
        exercises = db.execute(select(Exercise)).scalars().all()
        if not exercises:
            raise RuntimeError("No hay ejercicios en la base de datos. Arranca la API una vez para cargar el dataset.")

        import_survey_profiles(db, rows)
        delete_previous_generated_data(db)

        summaries = []
        total_routines = 0
        total_activities = 0
        total_activity_exercises = 0

        for row in rows:
            result = generate_user_data(db, row, exercises)
            summaries.append(result)
            total_routines += result["routines_created"]
            total_activities += result["activities_created"]
            total_activity_exercises += result["activity_exercises_created"]

        db.commit()

    write_summary_csv(summaries)
    write_report(rows, summaries, total_routines, total_activities, total_activity_exercises)

    print(f"OK: {total_routines} rutinas creadas")
    print(f"OK: {total_activities} actividades creadas")
    print(f"OK: {total_activity_exercises} ejercicios de actividad creados")
    print(f"Resumen EDA: {SUMMARY_PATH.relative_to(ROOT_DIR)}")
    print(f"Informe: {REPORT_PATH.relative_to(ROOT_DIR)}")


def import_survey_profiles(db, rows: list[dict[str, str]]) -> None:
    """Asegura que cada participante anonimizado exista como usuario."""
    for row in rows:
        import_row(db, row)
    db.flush()


def delete_previous_generated_data(db) -> None:
    """Elimina solo datos generados por este script para poder repetir el EDA."""
    survey_users = db.execute(select(User).where(User.username.like("survey_%"))).scalars().all()
    survey_user_ids = [user.id for user in survey_users]
    if not survey_user_ids:
        return

    generated_routines = (
        db.execute(
            select(Routine)
            .where(Routine.id_users.in_(survey_user_ids))
            .where(Routine.profile_snapshot.like(f"%{SOURCE}%"))
        )
        .scalars()
        .all()
    )
    for routine in generated_routines:
        db.delete(routine)

    generated_logs = (
        db.execute(
            select(WorkoutLog)
            .where(WorkoutLog.id_users.in_(survey_user_ids))
            .where(WorkoutLog.notes.like(f"%{SOURCE}%"))
        )
        .scalars()
        .all()
    )
    for log in generated_logs:
        db.delete(log)

    db.flush()


def generate_user_data(db, row: dict[str, str], exercises: list[Exercise]) -> dict[str, object]:
    """Crea una rutina y varias actividades simuladas para un participante."""
    username = row["username"]
    user = db.execute(select(User).where(User.username == username)).scalar_one()
    profile = latest_profile(db, user.id)
    derived = derive_training_profile(row)

    objective = db.execute(select(Objective).where(Objective.objective_name == row["objective"])).scalar_one_or_none()
    profile.id_objective = objective.id if objective else None
    profile.level = derived["level"]
    profile.environment = derived["environment"]
    profile.available_minutes = derived["available_minutes"]
    profile.training_days = derived["training_days"]

    routine = create_routine(db, user, row, profile, exercises, derived)
    activities_created, activity_exercises_created, minutes, calories = create_activity_logs(
        db,
        user,
        row,
        routine,
        derived,
    )

    return {
        "participant_id": row["participant_id"],
        "username": username,
        "objective": row["objective"],
        "level": derived["level"],
        "environment": derived["environment"],
        "age_group": row["age_group"],
        "gender": row["gender"],
        "province": row["province"],
        "bmi": row["bmi"],
        "disease_count": disease_count(row),
        "medicated": bool(row.get("medication_standardized")),
        "planned_training_days": derived["training_days"],
        "available_minutes": derived["available_minutes"],
        "adherence": derived["adherence"],
        "routines_created": 1,
        "activities_created": activities_created,
        "activity_exercises_created": activity_exercises_created,
        "total_activity_minutes": minutes,
        "total_activity_calories": round(calories, 1),
    }


def latest_profile(db, user_id: int) -> Profile:
    profile = (
        db.execute(select(Profile).where(Profile.id_users == user_id).order_by(Profile.created_at.desc()).limit(1))
        .scalars()
        .first()
    )
    if not profile:
        profile = Profile(id_users=user_id, level="principiante", environment="ambos", available_minutes=45, training_days=3)
        db.add(profile)
        db.flush()
    return profile


def derive_training_profile(row: dict[str, str]) -> dict[str, object]:
    """Deriva tiempo, dias, entorno y adherencia a partir del perfil limpio.

    La encuesta no recoge todas las variables que necesita el MVP, por eso se
    usan reglas simples y explicables basadas en edad, objetivo, nivel y salud.
    """
    level = row.get("level") or "principiante"
    objective = row.get("objective") or "mantenimiento"
    diseases = disease_count(row)
    medicated = bool(row.get("medication_standardized"))

    minutes = minutes_from_age(row.get("age_group"))
    if objective == "fuerza":
        minutes += 5
    elif objective == "perdida_grasa":
        minutes -= 5
    if diseases:
        minutes -= 5
    if medicated:
        minutes -= 5
    minutes = clamp_to_step(minutes, minimum=25, maximum=70, step=5)

    training_days = {"principiante": 3, "intermedio": 4, "avanzado": 5}.get(level, 3)
    if objective == "mantenimiento":
        training_days = max(2, training_days - 1)
    if diseases or medicated:
        training_days = max(2, training_days - 1)

    if level == "avanzado":
        environment = "gimnasio"
    elif level == "intermedio":
        environment = "ambos"
    elif objective == "fuerza":
        environment = "ambos"
    else:
        environment = "casa"

    adherence = {"principiante": 0.62, "intermedio": 0.76, "avanzado": 0.86}.get(level, 0.68)
    if diseases:
        adherence -= 0.08
    if medicated:
        adherence -= 0.05
    adherence = max(0.45, min(0.9, adherence))

    return {
        "level": level,
        "environment": environment,
        "available_minutes": minutes,
        "training_days": training_days,
        "adherence": round(adherence, 2),
    }


def minutes_from_age(age_group: str | None) -> int:
    return {
        "18-29": 55,
        "30-39": 50,
        "40-49": 45,
        "50-59": 40,
        "60-69": 35,
        "70+": 30,
    }.get(age_group or "", 45)


def create_routine(
    db,
    user: User,
    row: dict[str, str],
    profile: Profile,
    exercises: list[Exercise],
    derived: dict[str, object],
) -> Routine:
    """Guarda una rutina generada por el recomendador para el usuario."""
    profile_payload = {
        "username": user.username,
        "email": user.email,
        "name": profile.name,
        "lastname": profile.lastname,
        "gender": profile.gender,
        "province": profile.provincia,
        "weight": profile.weight or parse_float(row["weight_kg"]) or 70,
        "height": profile.height or parse_float(row["height_cm"]) or 170,
        "level": derived["level"],
        "objective": row["objective"],
        "environment": derived["environment"],
        "available_minutes": derived["available_minutes"],
        "training_days": derived["training_days"],
    }
    plan = build_routine(profile_payload, exercises)
    created_at = study_start(row) - timedelta(days=2)
    snapshot = {
        **profile_payload,
        "source": SOURCE,
        "participant_id": row["participant_id"],
        "age_group": row["age_group"],
        "bmi": row["bmi"],
        "diseases": split_pipe(row.get("diseases_standardized", "")),
        "medication": row.get("medication_standardized") or None,
        "adherence": derived["adherence"],
    }

    routine = Routine(
        id_users=user.id,
        objective=plan["objective"],
        level=plan["level"],
        environment=plan["environment"],
        available_minutes=plan["available_minutes"],
        estimated_minutes=plan["estimated_minutes"],
        estimated_calories=plan["estimated_calories"],
        profile_snapshot=json.dumps(snapshot, ensure_ascii=False),
        created_at=created_at,
    )
    db.add(routine)
    db.flush()

    for item in plan["exercises"]:
        db.add(
            RoutineExercise(
                routine_id=routine.id,
                exercise_id=item["exercise_id"],
                order_index=item["order"],
                sets=item["sets"],
                reps=item["reps"],
                rest_seconds=item["rest_seconds"],
                minutes=item["minutes"],
                calories=item["calories"],
                notes=item["notes"],
            )
        )

    db.flush()
    db.refresh(routine)
    return routine


def create_activity_logs(
    db,
    user: User,
    row: dict[str, str],
    routine: Routine,
    derived: dict[str, object],
) -> tuple[int, int, int, float]:
    """Simula seis semanas de entrenamientos con adherencia variable."""
    # La semilla por participante hace que el resultado sea reproducible aunque
    # incluya aleatoriedad en dias, duracion y ejercicios realizados.
    rng = random.Random(row["participant_id"])
    created = 0
    exercise_rows = 0
    total_minutes_all = 0
    total_calories_all = 0.0
    planned_days = int(derived["training_days"])
    adherence = float(derived["adherence"])
    weight = parse_float(row["weight_kg"]) or 70
    start = study_start(row)

    for week in range(6):
        week_start = start + timedelta(days=week * 7)
        for weekday in planned_weekdays(planned_days, rng):
            if rng.random() > adherence:
                continue

            # Las sesiones se colocan por la tarde para que el historial parezca
            # natural sin depender de datos personales reales.
            session_at = week_start + timedelta(days=weekday, hours=18 + rng.randint(0, 2), minutes=rng.choice([0, 15, 30, 45]))
            selected_items = select_session_exercises(list(routine.exercises), rng, row.get("objective", "mantenimiento"))
            log = WorkoutLog(
                id_users=user.id,
                total_minutes=0,
                total_calories=0,
                notes=json.dumps(
                    {
                        "source": SOURCE,
                        "participant_id": row["participant_id"],
                        "week": week + 1,
                        "planned_training_days": planned_days,
                        "adherence": adherence,
                    },
                    ensure_ascii=False,
                ),
                created_at=session_at,
            )
            db.add(log)
            db.flush()

            total_minutes = 0
            total_calories = 0.0
            for item in selected_items:
                minutes = varied_minutes(item.minutes, rng)
                calories = calories_from_met(item.exercise.met_estimate, weight, minutes)
                total_minutes += minutes
                total_calories += calories
                db.add(
                    WorkoutLogExercise(
                        log_id=log.id,
                        exercise_id=item.exercise_id,
                        minutes=minutes,
                        calories=calories,
                    )
                )
                exercise_rows += 1

            log.total_minutes = total_minutes
            log.total_calories = round(total_calories, 1)
            created += 1
            total_minutes_all += total_minutes
            total_calories_all += total_calories

    return created, exercise_rows, total_minutes_all, total_calories_all


def planned_weekdays(planned_days: int, rng: random.Random) -> list[int]:
    """Devuelve una distribucion semanal razonable para los dias de entreno."""
    presets = {
        2: [1, 4],
        3: [0, 2, 4],
        4: [0, 1, 3, 5],
        5: [0, 1, 2, 4, 5],
    }
    days = presets.get(planned_days, [0, 2, 4])
    if rng.random() < 0.35:
        days = sorted(rng.sample(range(6), k=min(planned_days, 6)))
    return days


def select_session_exercises(items: list[RoutineExercise], rng: random.Random, objective: str) -> list[RoutineExercise]:
    """Selecciona parte de la rutina para simular sesiones no siempre perfectas."""
    minimum = 3 if objective == "mantenimiento" else 4
    maximum = min(len(items), 6 if objective == "perdida_grasa" else 5)
    count = rng.randint(min(minimum, maximum), maximum)
    selected = sorted(rng.sample(items, k=count), key=lambda item: item.order_index)
    return selected


def varied_minutes(minutes: int, rng: random.Random) -> int:
    factor = rng.uniform(0.8, 1.2)
    return max(4, int(round(minutes * factor)))


def study_start(row: dict[str, str]) -> datetime:
    offset = int(row["participant_id"].replace("P", "")) % 5
    return datetime.now().replace(hour=8, minute=0, second=0, microsecond=0) - timedelta(days=43 + offset)


def write_summary_csv(rows: list[dict[str, object]]) -> None:
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return

    with SUMMARY_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    survey_rows: list[dict[str, str]],
    summaries: list[dict[str, object]],
    routines: int,
    activities: int,
    activity_exercises: int,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    total_minutes = sum(int(row["total_activity_minutes"]) for row in summaries)
    total_calories = sum(float(row["total_activity_calories"]) for row in summaries)
    avg_activities = activities / len(summaries) if summaries else 0

    REPORT_PATH.write_text(
        "\n".join(
            [
                "# Generacion de datos para EDA",
                "",
                f"- Fuente: `data/processed/survey_profiles_clean.csv`",
                f"- Marcador de datos sinteticos: `{SOURCE}`",
                f"- Usuarios de encuesta: {len(survey_rows)}",
                f"- Rutinas creadas: {routines}",
                f"- Actividades creadas: {activities}",
                f"- Ejercicios registrados en actividades: {activity_exercises}",
                f"- Actividades medias por usuario: {avg_activities:.1f}",
                f"- Minutos totales registrados: {total_minutes}",
                f"- Calorias totales estimadas: {total_calories:.1f}",
                f"- Resumen tabular: `data/processed/{SUMMARY_PATH.name}`",
                "",
                "## Criterios de generacion",
                "",
                "- Objetivo, nivel, peso, altura, provincia, genero, enfermedades y medicacion salen del CSV anonimizado.",
                "- Tiempo disponible y dias de entrenamiento se derivan de edad, nivel, objetivo y condiciones de salud.",
                "- El entorno se deriva de nivel/objetivo porque la encuesta no lo recogia explicitamente.",
                "- Las actividades simulan 6 semanas de adherencia al entrenamiento.",
                "- Las calorias usan la formula MET del recomendador de la app.",
            ]
        ),
        encoding="utf-8",
    )


def clamp_to_step(value: int, minimum: int, maximum: int, step: int) -> int:
    value = max(minimum, min(maximum, value))
    return round(value / step) * step


def disease_count(row: dict[str, str]) -> int:
    return len(split_pipe(row.get("diseases_standardized", "")))


def split_pipe(value: str) -> list[str]:
    return [item for item in (value or "").split("|") if item]


def parse_float(value: str | None) -> float | None:
    if not value:
        return None
    return float(value)


if __name__ == "__main__":
    main()
