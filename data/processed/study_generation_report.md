# Generacion de datos para EDA

- Fuente: `data/processed/survey_profiles_clean.csv`
- Marcador de datos sinteticos: `survey_eda_v1`
- Usuarios de encuesta: 32
- Rutinas creadas: 32
- Actividades creadas: 317
- Ejercicios registrados en actividades: 1415
- Actividades medias por usuario: 9.9
- Minutos totales registrados: 10635
- Calorias totales estimadas: 94482.8
- Resumen tabular: `data/processed/study_activity_summary.csv`

## Criterios de generacion

- Objetivo, nivel, peso, altura, provincia, genero, enfermedades y medicacion salen del CSV anonimizado.
- Tiempo disponible y dias de entrenamiento se derivan de edad, nivel, objetivo y condiciones de salud.
- El entorno se deriva de nivel/objetivo porque la encuesta no lo recogia explicitamente.
- Las actividades simulan 6 semanas de adherencia al entrenamiento.
- Las calorias usan la formula MET del recomendador de la app.