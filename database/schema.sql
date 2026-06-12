CREATE DATABASE IF NOT EXISTS fitbit_tfm
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE fitbit_tfm;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  email VARCHAR(160) UNIQUE,
  password_hash VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS objective (
  id INT AUTO_INCREMENT PRIMARY KEY,
  objective_name VARCHAR(80) NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS p_profile (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_users INT NOT NULL,
  id_objective INT,
  name VARCHAR(80),
  lastname VARCHAR(120),
  birthday DATE,
  gender VARCHAR(40),
  provincia VARCHAR(80),
  weight DECIMAL(5,2),
  height DECIMAL(5,2),
  level VARCHAR(40) NOT NULL,
  environment VARCHAR(40) NOT NULL,
  available_minutes INT NOT NULL,
  training_days INT NOT NULL DEFAULT 3,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_profile_users FOREIGN KEY (id_users) REFERENCES users(id),
  CONSTRAINT fk_profile_objective FOREIGN KEY (id_objective) REFERENCES objective(id)
);

CREATE TABLE IF NOT EXISTS diseases (
  id INT AUTO_INCREMENT PRIMARY KEY,
  disease_name VARCHAR(120) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS user_health (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_users INT NOT NULL,
  id_diseases INT,
  medication VARCHAR(255),
  CONSTRAINT fk_health_users FOREIGN KEY (id_users) REFERENCES users(id),
  CONSTRAINT fk_health_diseases FOREIGN KEY (id_diseases) REFERENCES diseases(id)
);

CREATE TABLE IF NOT EXISTS exercises (
  id VARCHAR(16) PRIMARY KEY,
  name VARCHAR(180) NOT NULL,
  category VARCHAR(80) NOT NULL,
  body_part VARCHAR(80) NOT NULL,
  equipment VARCHAR(120) NOT NULL,
  target VARCHAR(120) NOT NULL,
  muscle_group VARCHAR(120),
  secondary_muscles TEXT,
  instructions TEXT,
  image VARCHAR(255),
  gif_url VARCHAR(255),
  met_estimate DECIMAL(4,1) NOT NULL DEFAULT 5.0,
  environment_tags VARCHAR(120) NOT NULL DEFAULT 'home,gym'
);

CREATE TABLE IF NOT EXISTS routines (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_users INT,
  objective VARCHAR(80) NOT NULL,
  level VARCHAR(40) NOT NULL,
  environment VARCHAR(40) NOT NULL,
  available_minutes INT NOT NULL,
  estimated_minutes INT NOT NULL,
  estimated_calories DECIMAL(7,2) NOT NULL,
  profile_snapshot TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_routines_users FOREIGN KEY (id_users) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS routines_exercises (
  id INT AUTO_INCREMENT PRIMARY KEY,
  routine_id INT NOT NULL,
  exercise_id VARCHAR(16) NOT NULL,
  order_index INT NOT NULL,
  sets INT NOT NULL,
  reps VARCHAR(40) NOT NULL,
  rest_seconds INT NOT NULL,
  minutes INT NOT NULL,
  calories DECIMAL(7,2) NOT NULL,
  notes TEXT,
  CONSTRAINT fk_routine_item_routine FOREIGN KEY (routine_id) REFERENCES routines(id),
  CONSTRAINT fk_routine_item_exercise FOREIGN KEY (exercise_id) REFERENCES exercises(id),
  UNIQUE KEY uq_routine_exercise_order (routine_id, exercise_id, order_index)
);

CREATE TABLE IF NOT EXISTS historial_rutinas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_users INT,
  total_minutes INT NOT NULL,
  total_calories DECIMAL(7,2) NOT NULL,
  notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_history_users FOREIGN KEY (id_users) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS historial_rutinas_ejercicios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  log_id INT NOT NULL,
  exercise_id VARCHAR(16) NOT NULL,
  minutes INT NOT NULL,
  calories DECIMAL(7,2) NOT NULL,
  CONSTRAINT fk_history_item_log FOREIGN KEY (log_id) REFERENCES historial_rutinas(id),
  CONSTRAINT fk_history_item_exercise FOREIGN KEY (exercise_id) REFERENCES exercises(id)
);

INSERT IGNORE INTO objective (objective_name, description) VALUES
  ('fuerza', 'Fuerza'),
  ('perdida_grasa', 'Pérdida de grasa'),
  ('resistencia', 'Resistencia'),
  ('mantenimiento', 'Mantenimiento');
