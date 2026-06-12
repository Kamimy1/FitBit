# FitBit TFM

Aplicacion web para generar rutinas de entrenamiento personalizadas a partir de un perfil de usuario y un dataset de ejercicios.

## Stack

- Backend: Python + FastAPI
- Modelo: recomendador por reglas y puntuacion
- Datos: dataset local `exercises-dataset-main/data/exercises.json`
- Base de datos: MySQL en produccion/entrega, SQLite como demo local
- Frontend: HTML, CSS y JavaScript

## Ejecucion local

```powershell
cd D:\Evolve\TFM\FitBit
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

La web queda disponible en:

```text
http://127.0.0.1:8000
```

## MySQL

Crear la base de datos en el servidor MySQL:

```powershell
mysql -u root -p < database\schema.sql
```

Configurar la conexion en `.env`:

```env
DATABASE_URL=mysql+pymysql://USUARIO:PASSWORD_URL_ENCODED@HOST:3306/fitbit_tfm?charset=utf8mb4
```

El archivo `.env` esta ignorado por Git. No subas credenciales reales a GitHub.  
Si la contrasena contiene caracteres especiales, debe ir codificada para URL.

Ejemplo para codificar una contrasena:

```powershell
python -c "from urllib.parse import quote; print(quote('TU_PASSWORD', safe=''))"
```

Si no se define `DATABASE_URL`, la app usa SQLite local en `fitbit_tfm.db`.

## Flujo del MVP

1. El usuario introduce objetivo, nivel, entorno, tiempo disponible, peso y frecuencia semanal.
2. El backend carga el catalogo de ejercicios y calcula una puntuacion por objetivo, nivel, equipamiento y grupo muscular.
3. La API devuelve una rutina con ejercicios, series, repeticiones, descanso, minutos y calorias estimadas.
4. El usuario registra ejercicios realizados y el sistema guarda un historial basico de actividad.

## API principal

- `GET /api/health`
- `GET /api/options`
- `GET /api/exercises`
- `POST /api/routines/recommend`
- `POST /api/activity`
- `GET /api/history`

## Documentacion y entrega

La memoria, el EDA, la presentacion y el video final del proyecto estan dentro de:

```text
documentos_fitbit/
```

La presentacion esta preparada como pitch de producto y el video final se incluye como `Video_Presentacion_TFM.mp4`.
