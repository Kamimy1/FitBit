import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Exercise, Objective
from .recommender import OBJECTIVES, equipment_environment, estimate_met


def seed_objectives(db: Session) -> None:
    """Carga los objetivos base usados por el formulario y el recomendador."""
    existing = {row[0] for row in db.execute(select(Objective.objective_name)).all()}
    for key, config in OBJECTIVES.items():
        if key not in existing:
            db.add(
                Objective(
                    objective_name=key,
                    description=config["label"],
                )
            )
    db.commit()


def seed_exercises(db: Session, dataset_path: Path) -> int:
    if not dataset_path.exists():
        return 0

    # Si ya existe al menos un ejercicio, no se reimporta el JSON. Asi se evita
    # duplicar datos cada vez que se arranca la API durante la demo.
    existing_count = db.execute(select(Exercise.id).limit(1)).first()
    if existing_count:
        return 0

    with dataset_path.open("r", encoding="utf-8") as file:
        exercises = json.load(file)

    rows = []
    for item in exercises:
        instructions = item.get("instructions") or {}
        # El dataset puede traer instrucciones como diccionario por idioma o
        # como texto plano. Se normaliza a una cadena para guardarla en SQLite.
        if isinstance(instructions, dict):
            instructions_text = instructions.get("en") or next(iter(instructions.values()), "")
        else:
            instructions_text = str(instructions)

        rows.append(
            Exercise(
                id=str(item.get("id")),
                name=item.get("name") or "Exercise",
                category=item.get("category") or item.get("body_part") or "general",
                body_part=item.get("body_part") or item.get("category") or "general",
                equipment=item.get("equipment") or "body weight",
                target=item.get("target") or "general",
                muscle_group=item.get("muscle_group"),
                secondary_muscles=json.dumps(item.get("secondary_muscles") or []),
                instructions=instructions_text,
                image=item.get("image"),
                gif_url=item.get("gif_url"),
                # MET y entorno son campos derivados para que el catalogo pueda
                # recomendar y filtrar sin recalcularlo en cada peticion.
                met_estimate=estimate_met(item.get("category"), item.get("equipment"), item.get("target")),
                environment_tags=equipment_environment(item.get("equipment") or ""),
            )
        )

    db.add_all(rows)
    db.commit()
    return len(rows)
