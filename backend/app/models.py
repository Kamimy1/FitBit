from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    profiles: Mapped[list["Profile"]] = relationship(back_populates="user")
    routines: Mapped[list["Routine"]] = relationship(back_populates="user")
    workout_logs: Mapped[list["WorkoutLog"]] = relationship(back_populates="user")


class Objective(Base):
    __tablename__ = "objective"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    objective_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    profiles: Mapped[list["Profile"]] = relationship(back_populates="objective")


class Profile(Base):
    __tablename__ = "p_profile"

    # Un usuario puede tener varios perfiles en el tiempo. Cada rutina guarda el
    # perfil usado para que la recomendacion siga siendo trazable.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_users: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    id_objective: Mapped[int | None] = mapped_column(ForeignKey("objective.id"), nullable=True)
    name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lastname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provincia: Mapped[str | None] = mapped_column(String(80), nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    level: Mapped[str] = mapped_column(String(40), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    available_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    training_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="profiles")
    objective: Mapped[Objective | None] = relationship(back_populates="profiles")


class Disease(Base):
    __tablename__ = "diseases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    disease_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)


class UserHealth(Base):
    __tablename__ = "user_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_users: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    id_diseases: Mapped[int | None] = mapped_column(ForeignKey("diseases.id"), nullable=True)
    medication: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Exercise(Base):
    __tablename__ = "exercises"

    # Catalogo importado del JSON original, enriquecido con MET estimado y tags
    # de entorno para filtrar/recomendar sin depender del archivo fuente.
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    body_part: Mapped[str] = mapped_column(String(80), nullable=False)
    equipment: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    muscle_group: Mapped[str | None] = mapped_column(String(120), nullable=True)
    secondary_muscles: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gif_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    met_estimate: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    environment_tags: Mapped[str] = mapped_column(String(120), default="home,gym", nullable=False)

    routine_items: Mapped[list["RoutineExercise"]] = relationship(back_populates="exercise")


class Routine(Base):
    __tablename__ = "routines"

    # Cabecera de una recomendacion generada. Los ejercicios concretos se
    # guardan aparte para conservar orden, volumen y calorias.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_users: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    objective: Mapped[str] = mapped_column(String(80), nullable=False)
    level: Mapped[str] = mapped_column(String(40), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    available_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_calories: Mapped[float] = mapped_column(Float, nullable=False)
    profile_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User | None] = relationship(back_populates="routines")
    exercises: Mapped[list["RoutineExercise"]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineExercise.order_index",
    )


class RoutineExercise(Base):
    __tablename__ = "routines_exercises"
    __table_args__ = (UniqueConstraint("routine_id", "exercise_id", "order_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    routine_id: Mapped[int] = mapped_column(ForeignKey("routines.id"), nullable=False, index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[str] = mapped_column(String(40), nullable=False)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    routine: Mapped[Routine] = relationship(back_populates="exercises")
    exercise: Mapped[Exercise] = relationship(back_populates="routine_items")


class WorkoutLog(Base):
    __tablename__ = "historial_rutinas"

    # Actividades completadas por el usuario. No sustituyen a la rutina: sirven
    # para medir lo que realmente se ha registrado.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_users: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    total_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_calories: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User | None] = relationship(back_populates="workout_logs")
    exercises: Mapped[list["WorkoutLogExercise"]] = relationship(
        back_populates="log",
        cascade="all, delete-orphan",
    )


class WorkoutLogExercise(Base):
    __tablename__ = "historial_rutinas_ejercicios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_id: Mapped[int] = mapped_column(ForeignKey("historial_rutinas.id"), nullable=False, index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), nullable=False, index=True)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    calories: Mapped[float] = mapped_column(Float, nullable=False)

    log: Mapped[WorkoutLog] = relationship(back_populates="exercises")
    exercise: Mapped[Exercise] = relationship()
