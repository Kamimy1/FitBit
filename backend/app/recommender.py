import json
import math
import unicodedata
from dataclasses import dataclass
from typing import Any


HOME_EQUIPMENT = {
    "body weight",
    "band",
    "resistance band",
    "dumbbell",
    "kettlebell",
    "medicine ball",
    "stability ball",
    "bosu ball",
    "wheel roller",
    "roller",
    "weighted",
}

GYM_ONLY_HINTS = {
    "cable",
    "barbell",
    "smith machine",
    "leverage machine",
    "sled machine",
    "assisted",
    "ez barbell",
    "olympic barbell",
    "rope",
}

OBJECTIVES: dict[str, dict[str, Any]] = {
    "fuerza": {
        "label": "Fuerza",
        "targets": {"pectorals", "upper back", "lats", "glutes", "quads", "hamstrings", "delts", "triceps", "biceps"},
        "categories": {"chest", "back", "upper legs", "shoulders", "upper arms"},
        "equipment_bonus": {"barbell", "dumbbell", "cable", "smith machine", "leverage machine", "kettlebell"},
        "sets": {"principiante": 3, "intermedio": 4, "avanzado": 5},
        "reps": {"principiante": "8-10", "intermedio": "6-8", "avanzado": "5-6"},
        "rest": 90,
    },
    "perdida_grasa": {
        "label": "Pérdida de grasa",
        "targets": {"cardiovascular system", "abs", "glutes", "quads", "hamstrings", "calves"},
        "categories": {"cardio", "waist", "upper legs", "lower legs"},
        "equipment_bonus": {"body weight", "dumbbell", "kettlebell", "medicine ball", "band"},
        "sets": {"principiante": 3, "intermedio": 3, "avanzado": 4},
        "reps": {"principiante": "12-14", "intermedio": "14-16", "avanzado": "15-20"},
        "rest": 40,
    },
    "resistencia": {
        "label": "Resistencia",
        "targets": {"cardiovascular system", "abs", "calves", "glutes", "quads", "hamstrings", "delts"},
        "categories": {"cardio", "waist", "lower legs", "upper legs", "shoulders"},
        "equipment_bonus": {"body weight", "band", "resistance band", "dumbbell"},
        "sets": {"principiante": 2, "intermedio": 3, "avanzado": 4},
        "reps": {"principiante": "14-16", "intermedio": "16-20", "avanzado": "20-24"},
        "rest": 30,
    },
    "mantenimiento": {
        "label": "Mantenimiento",
        "targets": {"abs", "pectorals", "upper back", "glutes", "delts", "biceps", "triceps", "calves"},
        "categories": {"waist", "chest", "back", "upper legs", "shoulders", "upper arms", "lower legs"},
        "equipment_bonus": {"body weight", "dumbbell", "band", "cable", "kettlebell"},
        "sets": {"principiante": 2, "intermedio": 3, "avanzado": 4},
        "reps": {"principiante": "10-12", "intermedio": "10-14", "avanzado": "8-12"},
        "rest": 60,
    },
}

OBJECTIVE_ALIASES = {
    "fuerza": "fuerza",
    "strength": "fuerza",
    "perdida de grasa": "perdida_grasa",
    "perdida grasa": "perdida_grasa",
    "perdida_grasa": "perdida_grasa",
    "fat loss": "perdida_grasa",
    "resistencia": "resistencia",
    "endurance": "resistencia",
    "mantenimiento": "mantenimiento",
    "maintenance": "mantenimiento",
}

LEVELS = {"principiante", "intermedio", "avanzado"}
ENVIRONMENTS = {"casa", "ambos", "gimnasio"}


@dataclass(frozen=True)
class ExerciseCandidate:
    id: str
    name: str
    category: str
    body_part: str
    equipment: str
    target: str
    muscle_group: str | None
    secondary_muscles: list[str]
    instructions: str | None
    image: str | None
    gif_url: str | None
    met_estimate: float


def normalize(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return value.strip().lower()


def resolve_objective(value: str | None) -> str:
    key = normalize(value)
    return OBJECTIVE_ALIASES.get(key, "mantenimiento")


def resolve_level(value: str | None) -> str:
    key = normalize(value)
    return key if key in LEVELS else "principiante"


def resolve_environment(value: str | None) -> str:
    key = normalize(value)
    if key in {"ambos", "both"}:
        return "ambos"
    if key in {"gym", "gimnasio"}:
        return "gimnasio"
    return "casa"


def equipment_environment(equipment: str) -> str:
    equipment = normalize(equipment)
    if equipment in HOME_EQUIPMENT:
        return "home,gym"
    if equipment in GYM_ONLY_HINTS or any(hint in equipment for hint in GYM_ONLY_HINTS):
        return "gym"
    return "home,gym"


def estimate_met(category: str, equipment: str, target: str) -> float:
    category = normalize(category)
    equipment = normalize(equipment)
    target = normalize(target)

    base = {
        "cardio": 8.2,
        "waist": 4.7,
        "upper legs": 6.4,
        "lower legs": 5.4,
        "back": 6.0,
        "chest": 5.8,
        "shoulders": 5.4,
        "upper arms": 4.8,
        "lower arms": 3.8,
        "neck": 2.8,
    }.get(category, 5.0)

    if equipment in {"barbell", "smith machine", "leverage machine", "sled machine"}:
        base += 0.9
    elif equipment in {"dumbbell", "kettlebell", "cable"}:
        base += 0.5
    elif equipment in {"body weight", "band", "resistance band"}:
        base += 0.1

    if target in {"cardiovascular system", "glutes", "quads", "hamstrings"}:
        base += 0.4

    return round(min(max(base, 2.5), 10.0), 1)


def calories_from_met(met: float, weight_kg: float, minutes: int) -> float:
    return round((met * 3.5 * weight_kg / 200) * minutes, 1)


def candidate_from_model(exercise: Any) -> ExerciseCandidate:
    secondary = exercise.secondary_muscles
    if isinstance(secondary, str):
        try:
            secondary = json.loads(secondary)
        except json.JSONDecodeError:
            secondary = []
    return ExerciseCandidate(
        id=str(exercise.id),
        name=exercise.name,
        category=normalize(exercise.category),
        body_part=normalize(exercise.body_part),
        equipment=normalize(exercise.equipment),
        target=normalize(exercise.target),
        muscle_group=normalize(exercise.muscle_group),
        secondary_muscles=secondary or [],
        instructions=exercise.instructions,
        image=exercise.image,
        gif_url=exercise.gif_url,
        met_estimate=float(exercise.met_estimate or estimate_met(exercise.category, exercise.equipment, exercise.target)),
    )


def score_exercise(exercise: ExerciseCandidate, objective: str, level: str, environment: str) -> float:
    config = OBJECTIVES[objective]
    score = 0.0

    if exercise.category in config["categories"]:
        score += 35
    if exercise.target in config["targets"]:
        score += 30
    if exercise.muscle_group and exercise.muscle_group in config["targets"]:
        score += 12
    if exercise.equipment in config["equipment_bonus"]:
        score += 16

    env_tags = equipment_environment(exercise.equipment)
    if environment == "casa":
        if "home" not in env_tags:
            return -1000
        if exercise.equipment in {"body weight", "band", "resistance band"}:
            score += 12
    elif environment == "ambos":
        if env_tags != "home,gym":
            return -1000
        if exercise.equipment in {"body weight", "band", "resistance band", "dumbbell", "kettlebell"}:
            score += 12
    else:
        if "gym" in env_tags:
            score += 8
        if exercise.equipment in {"barbell", "cable", "smith machine", "leverage machine"}:
            score += 8

    if level == "principiante":
        if exercise.equipment in {"body weight", "band", "resistance band", "dumbbell"}:
            score += 14
        if exercise.equipment in {"barbell", "smith machine", "sled machine"}:
            score -= 10
    elif level == "intermedio":
        if exercise.equipment in {"dumbbell", "kettlebell", "cable", "body weight"}:
            score += 10
    else:
        if exercise.equipment in {"barbell", "cable", "smith machine", "leverage machine", "kettlebell"}:
            score += 12

    score += exercise.met_estimate * (2.4 if objective == "perdida_grasa" else 1.2)
    return score


def target_exercise_count(minutes: int) -> int:
    if minutes <= 25:
        return 4
    if minutes <= 40:
        return 5
    if minutes <= 55:
        return 6
    return 8


def build_routine(profile: dict[str, Any], exercises: list[Any]) -> dict[str, Any]:
    objective = resolve_objective(profile.get("objective"))
    level = resolve_level(profile.get("level"))
    environment = resolve_environment(profile.get("environment"))
    minutes = int(profile.get("available_minutes") or 45)
    weight = float(profile.get("weight") or 70)
    count = target_exercise_count(minutes)
    minutes_per_exercise = max(4, math.floor(minutes / count))
    config = OBJECTIVES[objective]

    candidates = [candidate_from_model(exercise) for exercise in exercises]
    ranked = sorted(
        candidates,
        key=lambda item: score_exercise(item, objective, level, environment),
        reverse=True,
    )

    selected: list[ExerciseCandidate] = []
    category_counter: dict[str, int] = {}
    target_counter: dict[str, int] = {}

    for candidate in ranked:
        if score_exercise(candidate, objective, level, environment) < 0:
            continue
        category_limit = 2 if count <= 5 else 3
        if category_counter.get(candidate.category, 0) >= category_limit:
            continue
        if target_counter.get(candidate.target, 0) >= 2:
            continue
        selected.append(candidate)
        category_counter[candidate.category] = category_counter.get(candidate.category, 0) + 1
        target_counter[candidate.target] = target_counter.get(candidate.target, 0) + 1
        if len(selected) == count:
            break

    if len(selected) < count:
        already = {exercise.id for exercise in selected}
        for candidate in ranked:
            if candidate.id not in already and score_exercise(candidate, objective, level, environment) >= 0:
                selected.append(candidate)
                already.add(candidate.id)
            if len(selected) == count:
                break

    routine_items = []
    total_calories = 0.0
    for index, exercise in enumerate(selected, start=1):
        item_calories = calories_from_met(exercise.met_estimate, weight, minutes_per_exercise)
        total_calories += item_calories
        routine_items.append(
            {
                "order": index,
                "exercise_id": exercise.id,
                "name": exercise.name,
                "category": exercise.category,
                "body_part": exercise.body_part,
                "equipment": exercise.equipment,
                "target": exercise.target,
                "muscle_group": exercise.muscle_group,
                "instructions": exercise.instructions,
                "image": exercise.image,
                "gif_url": exercise.gif_url,
                "sets": config["sets"][level],
                "reps": config["reps"][level],
                "rest_seconds": config["rest"],
                "minutes": minutes_per_exercise,
                "calories": item_calories,
                "notes": recommendation_note(objective, level, exercise),
            }
        )

    return {
        "objective": objective,
        "objective_label": config["label"],
        "level": level,
        "environment": environment,
        "available_minutes": minutes,
        "estimated_minutes": minutes_per_exercise * len(routine_items),
        "estimated_calories": round(total_calories, 1),
        "exercises": routine_items,
    }


def recommendation_note(objective: str, level: str, exercise: ExerciseCandidate) -> str:
    if objective == "fuerza":
        return "Prioriza técnica y descanso completo entre series."
    if objective == "perdida_grasa":
        return "Mantiene ritmo medio-alto y descansos cortos."
    if objective == "resistencia":
        return "Busca continuidad y control del esfuerzo."
    if level == "principiante" and exercise.equipment == "body weight":
        return "Adecuado para consolidar base técnica."
    return "Ejercicio equilibrado para el objetivo indicado."
