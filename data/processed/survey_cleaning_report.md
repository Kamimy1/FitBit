# Informe de limpieza de encuesta

- Respuestas origen: 32
- Registros publicos anonimizados: 32
- Registros sensibles locales: 32
- Fechas de nacimiento invalidas o corregidas: 5
- Salida publica: `data/processed/survey_profiles_clean.csv`
- Salida privada ignorada por Git: `data/private/survey_profiles_sensitive.csv`


## Objetivos normalizados

- fuerza: 16
- perdida_grasa: 13
- mantenimiento: 3

## Niveles normalizados

- principiante: 24
- intermedio: 6
- avanzado: 2

## Generos normalizados

- hombre: 16
- mujer: 16

## Provincias

- Sevilla: 30
- Málaga: 1
- Madrid: 1

## Reglas principales

- Los nombres y apellidos del dataset publico son ficticios.
- Se eliminan nombres reales, apellidos reales, fecha de nacimiento exacta, timestamp y datos sanitarios crudos del dataset publico.
- Los participantes se renombran como `P001`, `P002`, etc.
- La edad exacta se agrupa por decadas en el dataset publico.
- Pesos y alturas pasan de coma decimal a punto decimal.
- Altura se guarda en metros y centimetros.
- `Medio` se normaliza como `intermedio`.
- Objetivos libres se agrupan en `perdida_grasa`, `fuerza`, `resistencia` o `mantenimiento`.
- Enfermedades y medicacion se publican solo como categorias estandarizadas.
