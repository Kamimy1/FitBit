import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Exercise, Objective, Profile, Routine, RoutineExercise, User, WorkoutLog, WorkoutLogExercise
from .recommender import (
    ENVIRONMENTS,
    LEVELS,
    OBJECTIVES,
    build_routine,
    calories_from_met,
    resolve_environment,
    resolve_level,
    resolve_objective,
)
from .schemas import ActivityInput, ActivityOut, ExerciseListOut, ExerciseOut, ProfileInput, RoutineExerciseOut, RoutineOut
from .seed import seed_exercises, seed_objectives


# La API sirve tanto el backend como el frontend estatico para que el MVP se
# pueda lanzar localmente con un unico proceso.
ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"


def project_path(value: str | None, default: Path) -> Path:
    """Permite cambiar rutas por .env sin romper las rutas relativas del repo."""
    path = Path(value) if value else default
    return path.resolve() if path.is_absolute() else (ROOT_DIR / path).resolve()


DATASET_ROOT = project_path(os.getenv("DATASET_ROOT"), ROOT_DIR / "exercises-dataset-main")
DATASET_PATH = project_path(os.getenv("DATASET_PATH"), DATASET_ROOT / "data" / "exercises.json")

HOME_CATALOG_EQUIPMENT = {
    "body weight",
    "band",
    "resistance band",
    "medicine ball",
    "stability ball",
    "bosu ball",
    "roller",
    "wheel roller",
}

BOTH_CATALOG_EQUIPMENT = {
    "dumbbell",
    "kettlebell",
    "weighted",
}

app = FastAPI(
    title="FitBit TFM API",
    description="API REST para generación de rutinas personalizadas.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
if (DATASET_ROOT / "images").exists():
    app.mount("/dataset/images", StaticFiles(directory=DATASET_ROOT / "images"), name="dataset_images")
if (DATASET_ROOT / "videos").exists():
    app.mount("/dataset/videos", StaticFiles(directory=DATASET_ROOT / "videos"), name="dataset_videos")


@app.on_event("startup")
def startup() -> None:
    # Crea las tablas y carga objetivos/ejercicios solo si aun no existen.
    # Esto mantiene el arranque idempotente para desarrollo y demostracion.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_objectives(db)
        seed_exercises(db, DATASET_PATH)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict:
    exercise_count = db.execute(select(Exercise.id)).all()
    return {
        "status": "ok",
        "exercise_count": len(exercise_count),
        "dataset_path": str(DATASET_PATH),
    }


@app.get("/api/options")
def options() -> dict:
    return {
        "objectives": [{"value": key, "label": value["label"]} for key, value in OBJECTIVES.items()],
        "levels": [{"value": value, "label": value.capitalize()} for value in sorted(LEVELS)],
        "environments": [
            {"value": "casa", "label": "Casa"},
            {"value": "ambos", "label": "Ambos"},
            {"value": "gimnasio", "label": "Gimnasio"},
        ],
    }


@app.get("/api/users")
def list_users(db: Session = Depends(get_db)) -> dict:
    users = db.execute(select(User).order_by(User.username)).scalars().all()
    items = []
    for user in users:
        profile = (
            db.execute(
                select(Profile)
                .where(Profile.id_users == user.id)
                .order_by(Profile.created_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        items.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "name": profile.name if profile else None,
                "lastname": profile.lastname if profile else None,
                "province": profile.provincia if profile else None,
                "weight": profile.weight if profile else None,
                "height": profile.height if profile else None,
                "level": profile.level if profile else None,
                "objective": profile.objective.objective_name if profile and profile.objective else None,
                "environment": profile.environment if profile else None,
                "available_minutes": profile.available_minutes if profile else None,
                "training_days": profile.training_days if profile else None,
                "label": user.username if not user.email else f"{user.username} ({user.email})",
            }
        )
    return {"items": items}


@app.get("/api/exercise-filters")
def exercise_filters(db: Session = Depends(get_db)) -> dict:
    def distinct_values(column) -> list[str]:
        # Los filtros salen de los datos reales, asi no se quedan desactualizados
        # si cambia el catalogo de ejercicios.
        return [
            value
            for value in db.execute(select(column).where(column.is_not(None)).distinct().order_by(column)).scalars().all()
            if value
        ]

    return {
        "environments": [
            {"value": "casa", "label": "Casa"},
            {"value": "ambas", "label": "Ambas"},
            {"value": "gimnasio", "label": "Gimnasio"},
        ],
        "categories": distinct_values(Exercise.category),
        "targets": distinct_values(Exercise.target),
        "equipment": distinct_values(Exercise.equipment),
    }


@app.get("/api/exercises", response_model=ExerciseListOut)
def list_exercises(
    query: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    category: str | None = Query(default=None),
    target: str | None = Query(default=None),
    equipment: str | None = Query(default=None),
    sort: str = Query(default="name"),
    limit: int = Query(default=30, ge=1, le=120),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ExerciseListOut:
    conditions = []
    if query:
        pattern = f"%{query}%"
        conditions.append(
            or_(
                Exercise.name.ilike(pattern),
                Exercise.target.ilike(pattern),
                Exercise.category.ilike(pattern),
                Exercise.equipment.ilike(pattern),
            )
        )
    env_filter = (environment or "casa").strip().lower()
    # El catalogo usa filtros mas estrictos que el recomendador para que el
    # usuario vea claramente que ejercicios son de casa, ambos o gimnasio.
    if env_filter == "casa":
        conditions.append(Exercise.equipment.in_(HOME_CATALOG_EQUIPMENT))
    elif env_filter == "ambas":
        conditions.append(Exercise.equipment.in_(BOTH_CATALOG_EQUIPMENT))
    elif env_filter == "gimnasio":
        conditions.append(Exercise.environment_tags == "gym")
    if category:
        conditions.append(Exercise.category == category)
    if target:
        conditions.append(Exercise.target == target)
    if equipment:
        conditions.append(Exercise.equipment == equipment)

    statement = select(Exercise)
    count_statement = select(func.count()).select_from(Exercise)
    for condition in conditions:
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    sort_map = {
        "name": Exercise.name.asc(),
        "category": Exercise.category.asc(),
        "equipment": Exercise.equipment.asc(),
        "calories_desc": Exercise.met_estimate.desc(),
        "calories_asc": Exercise.met_estimate.asc(),
    }
    statement = statement.order_by(sort_map.get(sort, Exercise.name.asc()), Exercise.name.asc())

    total = db.execute(count_statement).scalar_one()
    rows = db.execute(statement.offset(offset).limit(limit)).scalars().all()
    return ExerciseListOut(
        items=[exercise_to_out(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post("/api/routines/recommend", response_model=RoutineOut)
def recommend_routine(payload: ProfileInput, db: Session = Depends(get_db)) -> RoutineOut:
    exercises = db.execute(select(Exercise)).scalars().all()
    if not exercises:
        raise HTTPException(status_code=503, detail="No hay ejercicios cargados en la base de datos.")

    # Se guarda el perfil usado para que cada recomendacion quede asociada al
    # usuario y se pueda consultar despues en el historial.
    user = get_or_create_user(db, payload.username, payload.email)
    objective_key = resolve_objective(payload.objective)
    objective = db.execute(select(Objective).where(Objective.objective_name == objective_key)).scalar_one_or_none()

    profile = Profile(
        id_users=user.id,
        id_objective=objective.id if objective else None,
        name=payload.name,
        lastname=payload.lastname,
        birthday=payload.birthday,
        gender=payload.gender,
        provincia=payload.province,
        weight=payload.weight,
        height=payload.height,
        level=resolve_level(payload.level),
        environment=resolve_environment(payload.environment),
        available_minutes=payload.available_minutes,
        training_days=payload.training_days,
    )
    db.add(profile)
    db.flush()

    # La logica de recomendacion vive fuera de FastAPI para poder probarla y
    # explicarla como modulo independiente.
    routine_plan = build_routine(payload.model_dump(), exercises)
    routine = Routine(
        id_users=user.id,
        objective=routine_plan["objective"],
        level=routine_plan["level"],
        environment=routine_plan["environment"],
        available_minutes=routine_plan["available_minutes"],
        estimated_minutes=routine_plan["estimated_minutes"],
        estimated_calories=routine_plan["estimated_calories"],
        profile_snapshot=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
    )
    db.add(routine)
    db.flush()

    # Se persiste cada ejercicio recomendado con sus series, repeticiones,
    # descanso y calorias para congelar la rutina generada en ese momento.
    exercise_map = {exercise.id: exercise for exercise in exercises}
    for item in routine_plan["exercises"]:
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
    db.commit()
    db.refresh(routine)

    return routine_to_out(routine, exercise_map)


@app.get("/api/routines/{routine_id}", response_model=RoutineOut)
def routine_detail(routine_id: int, db: Session = Depends(get_db)) -> RoutineOut:
    routine = db.execute(select(Routine).where(Routine.id == routine_id)).scalar_one_or_none()
    if not routine:
        raise HTTPException(status_code=404, detail="Rutina no encontrada.")
    return routine_to_out(routine)


@app.post("/api/activity", response_model=ActivityOut)
def save_activity(payload: ActivityInput, db: Session = Depends(get_db)) -> ActivityOut:
    user = get_or_create_user(db, payload.username, payload.email)
    ids = [entry.exercise_id for entry in payload.entries]
    exercises = db.execute(select(Exercise).where(Exercise.id.in_(ids))).scalars().all()
    exercise_map = {exercise.id: exercise for exercise in exercises}
    if len(exercise_map) != len(set(ids)):
        raise HTTPException(status_code=404, detail="Alguno de los ejercicios no existe.")

    total_minutes = sum(entry.minutes for entry in payload.entries)
    total_calories = 0.0
    log = WorkoutLog(id_users=user.id, total_minutes=total_minutes, total_calories=0, notes=payload.notes)
    db.add(log)
    db.flush()

    # Las calorias se recalculan con el peso indicado al registrar la actividad,
    # porque puede no coincidir con el peso guardado en el perfil original.
    response_entries = []
    for entry in payload.entries:
        exercise = exercise_map[entry.exercise_id]
        calories = calories_from_met(exercise.met_estimate, payload.weight, entry.minutes)
        total_calories += calories
        db.add(WorkoutLogExercise(log_id=log.id, exercise_id=exercise.id, minutes=entry.minutes, calories=calories))
        response_entries.append(
            {
                "exercise_id": exercise.id,
                "name": exercise.name,
                "minutes": entry.minutes,
                "calories": calories,
            }
        )

    log.total_calories = round(total_calories, 1)
    db.commit()
    db.refresh(log)
    return ActivityOut(
        id=log.id,
        total_minutes=log.total_minutes,
        total_calories=log.total_calories,
        created_at=log.created_at,
        exercises=response_entries,
    )


@app.get("/api/activity/{log_id}", response_model=ActivityOut)
def activity_detail(log_id: int, db: Session = Depends(get_db)) -> ActivityOut:
    log = db.execute(select(WorkoutLog).where(WorkoutLog.id == log_id)).scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")

    return ActivityOut(
        id=log.id,
        total_minutes=log.total_minutes,
        total_calories=log.total_calories,
        created_at=log.created_at,
        exercises=[
            {
                "exercise_id": item.exercise_id,
                "name": item.exercise.name,
                "target": item.exercise.target,
                "equipment": item.exercise.equipment,
                "image_url": media_url(item.exercise.image, "images"),
                "minutes": item.minutes,
                "calories": item.calories,
            }
            for item in log.exercises
        ],
    )


@app.get("/api/history")
def history(username: str = "", email: str | None = None, db: Session = Depends(get_db)) -> dict:
    user = find_user_for_history(db, username, email)
    if not user:
        return {"routines": [], "activities": []}

    # Se limita el historial para mantener la pantalla rapida y enfocada en los
    # ultimos registros de la demo.
    routines = (
        db.execute(select(Routine).where(Routine.id_users == user.id).order_by(Routine.created_at.desc()).limit(5))
        .scalars()
        .all()
    )
    activities = (
        db.execute(select(WorkoutLog).where(WorkoutLog.id_users == user.id).order_by(WorkoutLog.created_at.desc()).limit(8))
        .scalars()
        .all()
    )

    return {
        "routines": [
            {
                "id": routine.id,
                "objective": routine.objective,
                "level": routine.level,
                "environment": routine.environment,
                "estimated_minutes": routine.estimated_minutes,
                "estimated_calories": routine.estimated_calories,
                "created_at": routine.created_at,
            }
            for routine in routines
        ],
        "activities": [
            {
                "id": activity.id,
                "total_minutes": activity.total_minutes,
                "total_calories": activity.total_calories,
                "created_at": activity.created_at,
            }
            for activity in activities
        ],
    }


def find_user_for_history(db: Session, username: str, email: str | None) -> User | None:
    username_key = username.strip().lower()
    if username_key:
        user = db.execute(select(User).where(User.username == username_key)).scalar_one_or_none()
        if user:
            return user

    if email:
        return (
            db.execute(select(User).where(User.email == email.strip()).order_by(User.id.desc()).limit(1))
            .scalars()
            .first()
        )

    return None


def get_or_create_user(db: Session, username: str, email: str | None) -> User:
    username = username.strip().lower() or "demo"
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user:
        if email and not user.email:
            user.email = email
            db.flush()
        return user
    user = User(username=username, email=email)
    db.add(user)
    db.flush()
    return user


def exercise_to_out(exercise: Exercise) -> ExerciseOut:
    return ExerciseOut(
        id=exercise.id,
        name=exercise.name,
        category=exercise.category,
        body_part=exercise.body_part,
        equipment=exercise.equipment,
        target=exercise.target,
        muscle_group=exercise.muscle_group,
        instructions=exercise.instructions,
        image_url=media_url(exercise.image, "images"),
        gif_url=media_url(exercise.gif_url, "videos"),
        met_estimate=exercise.met_estimate,
    )


def routine_to_out(routine: Routine, exercise_map: dict[str, Exercise] | None = None) -> RoutineOut:
    items = []
    for item in routine.exercises:
        exercise = item.exercise if item.exercise else exercise_map[item.exercise_id]
        items.append(
            RoutineExerciseOut(
                order=item.order_index,
                exercise=exercise_to_out(exercise),
                sets=item.sets,
                reps=item.reps,
                rest_seconds=item.rest_seconds,
                minutes=item.minutes,
                calories=item.calories,
                notes=item.notes,
            )
        )

    return RoutineOut(
        id=routine.id,
        objective=routine.objective,
        objective_label=OBJECTIVES[routine.objective]["label"],
        level=routine.level,
        environment=routine.environment,
        available_minutes=routine.available_minutes,
        estimated_minutes=routine.estimated_minutes,
        estimated_calories=routine.estimated_calories,
        created_at=routine.created_at,
        exercises=items,
    )


def media_url(path: str | None, folder: str) -> str | None:
    if not path:
        return None
    filename = Path(path).name
    return f"/dataset/{folder}/{filename}"
