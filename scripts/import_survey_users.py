import csv
import sys
from pathlib import Path

from sqlalchemy import delete, select


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.database import Base, SessionLocal, engine  # noqa: E402
from backend.app.models import Disease, Objective, Profile, User, UserHealth  # noqa: E402
from backend.app.recommender import OBJECTIVES  # noqa: E402


INPUT_PATH = ROOT_DIR / "data" / "processed" / "survey_profiles_clean.csv"


def main() -> None:
    """Importa perfiles anonimizados de encuesta a la base de datos local."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"No existe el CSV limpio: {INPUT_PATH}")

    Base.metadata.create_all(bind=engine)
    rows = read_rows()

    with SessionLocal() as db:
        ensure_objectives(db)
        imported = 0
        for row in rows:
            import_row(db, row)
            imported += 1
        db.commit()

    print(f"OK: {imported} usuarios de encuesta importados/actualizados")


def read_rows() -> list[dict[str, str]]:
    with INPUT_PATH.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def ensure_objectives(db) -> None:
    """Asegura que la base tenga los objetivos que espera el recomendador."""
    existing = {name for name in db.execute(select(Objective.objective_name)).scalars().all()}
    for key, config in OBJECTIVES.items():
        if key not in existing:
            db.add(Objective(objective_name=key, description=config["label"]))
    db.flush()


def import_row(db, row: dict[str, str]) -> None:
    """Crea o actualiza un usuario de encuesta y su perfil principal."""
    username = row["username"]
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user:
        user = User(username=username, email=f"{username}@example.invalid")
        db.add(user)
        db.flush()
    else:
        user.email = user.email or f"{username}@example.invalid"

    objective = db.execute(select(Objective).where(Objective.objective_name == row["objective"])).scalar_one_or_none()

    profile = db.execute(select(Profile).where(Profile.id_users == user.id).limit(1)).scalar_one_or_none()
    if not profile:
        profile = Profile(id_users=user.id, level=row["level"], environment="ambos", available_minutes=45)
        db.add(profile)

    profile.id_objective = objective.id if objective else None
    profile.name = row["first_name"]
    profile.lastname = row["last_name"]
    profile.gender = row["gender"]
    profile.provincia = row["province"]
    profile.weight = parse_float(row["weight_kg"])
    profile.height = parse_float(row["height_cm"])
    profile.level = row["level"] or "principiante"
    profile.environment = "ambos"
    profile.available_minutes = 45
    profile.training_days = 3

    # Se borran las condiciones previas del usuario antes de volver a cargar el
    # CSV, para que ejecutar el script dos veces deje el mismo resultado.
    db.execute(delete(UserHealth).where(UserHealth.id_users == user.id))
    diseases = split_pipe(row.get("diseases_standardized", ""))
    medication = row.get("medication_standardized") or None

    if diseases:
        for disease_name in diseases:
            disease = get_or_create_disease(db, disease_name)
            db.add(UserHealth(id_users=user.id, id_diseases=disease.id, medication=medication))
    elif medication:
        db.add(UserHealth(id_users=user.id, id_diseases=None, medication=medication))


def get_or_create_disease(db, disease_name: str) -> Disease:
    disease = db.execute(select(Disease).where(Disease.disease_name == disease_name)).scalar_one_or_none()
    if disease:
        return disease
    disease = Disease(disease_name=disease_name)
    db.add(disease)
    db.flush()
    return disease


def split_pipe(value: str) -> list[str]:
    return [item for item in (value or "").split("|") if item]


def parse_float(value: str) -> float | None:
    if not value:
        return None
    return float(value)


if __name__ == "__main__":
    main()
