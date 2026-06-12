from datetime import date, datetime

from pydantic import BaseModel, Field


class ProfileInput(BaseModel):
    username: str = Field(default="demo", min_length=2, max_length=80)
    email: str | None = Field(default=None, max_length=160)
    name: str | None = Field(default=None, max_length=80)
    lastname: str | None = Field(default=None, max_length=120)
    birthday: date | None = None
    gender: str | None = Field(default=None, max_length=40)
    province: str | None = Field(default=None, max_length=80)
    weight: float = Field(default=70, ge=35, le=220)
    height: float | None = Field(default=None, ge=120, le=230)
    level: str = "principiante"
    objective: str = "mantenimiento"
    environment: str = "casa"
    available_minutes: int = Field(default=45, ge=15, le=120)
    training_days: int = Field(default=3, ge=1, le=7)


class ExerciseOut(BaseModel):
    id: str
    name: str
    category: str
    body_part: str
    equipment: str
    target: str
    muscle_group: str | None = None
    instructions: str | None = None
    image_url: str | None = None
    gif_url: str | None = None
    met_estimate: float


class ExerciseListOut(BaseModel):
    items: list[ExerciseOut]
    total: int
    limit: int
    offset: int


class RoutineExerciseOut(BaseModel):
    order: int
    exercise: ExerciseOut
    sets: int
    reps: str
    rest_seconds: int
    minutes: int
    calories: float
    notes: str | None = None


class RoutineOut(BaseModel):
    id: int | None = None
    objective: str
    objective_label: str
    level: str
    environment: str
    available_minutes: int
    estimated_minutes: int
    estimated_calories: float
    created_at: datetime | None = None
    exercises: list[RoutineExerciseOut]


class ActivityEntryInput(BaseModel):
    exercise_id: str
    minutes: int = Field(ge=1, le=240)


class ActivityInput(BaseModel):
    username: str = Field(default="demo", min_length=2, max_length=80)
    email: str | None = Field(default=None, max_length=160)
    weight: float = Field(default=70, ge=35, le=220)
    notes: str | None = Field(default=None, max_length=500)
    entries: list[ActivityEntryInput] = Field(min_length=1)


class ActivityOut(BaseModel):
    id: int
    total_minutes: int
    total_calories: float
    created_at: datetime
    exercises: list[dict]
