import csv
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT_DIR.parent / "Recogida de datos para TFM FITBIT.csv"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
PRIVATE_DIR = ROOT_DIR / "data" / "private"
PUBLIC_OUTPUT = PROCESSED_DIR / "survey_profiles_clean.csv"
PRIVATE_OUTPUT = PRIVATE_DIR / "survey_profiles_sensitive.csv"
REPORT_OUTPUT = PROCESSED_DIR / "survey_cleaning_report.md"
TODAY = date(2026, 6, 3)


PUBLIC_FIELDS = [
    "participant_id",
    "username",
    "first_name",
    "last_name",
    "age_group",
    "gender",
    "province",
    "weight_kg",
    "height_cm",
    "height_m",
    "bmi",
    "level",
    "objective",
    "diseases_standardized",
    "medication_standardized",
    "quality_notes",
]

PRIVATE_FIELDS = PUBLIC_FIELDS + [
    "birthdate",
    "age",
    "objective_raw",
    "has_disease",
    "disease_count",
    "has_medication",
    "source_timestamp",
    "original_first_name",
    "original_last_name",
    "diseases_standardized",
    "diseases_raw",
    "medication_standardized",
    "medication_raw",
]

FAKE_FIRST_NAMES_BY_GENDER = {
    "hombre": [
        "Hugo",
        "Mateo",
        "Daniel",
        "Adrian",
        "Sergio",
        "Alvaro",
        "Mario",
        "Pablo",
        "Javier",
        "Diego",
        "Ruben",
        "Marcos",
        "Leo",
        "Bruno",
        "Eric",
        "Gael",
        "Manuel",
        "Carlos",
        "Victor",
        "Raul",
    ],
    "mujer": [
        "Paula",
        "Lucia",
        "Irene",
        "Marta",
        "Clara",
        "Nuria",
        "Elena",
        "Laura",
        "Celia",
        "Sara",
        "Aitana",
        "Noa",
        "Vega",
        "Alba",
        "Ines",
        "Carmen",
        "Sofia",
        "Julia",
        "Valeria",
        "Emma",
    ],
    "otro": [
        "Alex",
        "Sam",
        "Nico",
        "Ariel",
        "Dani",
        "Noel",
    ],
}

FAKE_LAST_NAMES = [
    "Navarro Soler",
    "Martin Vega",
    "Santos Molina",
    "Romero Vidal",
    "Lopez Rivas",
    "Castro Leon",
    "Ortega Marin",
    "Gil Herrera",
    "Serrano Campos",
    "Ruiz Arroyo",
    "Morales Cano",
    "Iglesias Duran",
    "Ramos Fuentes",
    "Prieto Galan",
    "Vargas Nieto",
    "Carrasco Mora",
    "Delgado Rojas",
    "Sanz Robledo",
    "Cortes Pardo",
    "Reyes Lobo",
    "Mendez Bravo",
    "Pascual Mesa",
    "Ferrer Lozano",
    "Herrero Luna",
    "Vila Torres",
    "Navas Costa",
    "Blanco Rey",
    "Molina Abril",
    "Pena Soria",
    "Cruz Valero",
    "Campos Riera",
    "Soler Bravo",
]


DISEASE_KEYWORDS = [
    ("cefalea", "cefalea_tensional_cronica"),
    ("colitis ulcerosa", "colitis_ulcerosa"),
    ("esclerosis multiple", "esclerosis_multiple"),
    ("artritis reumatoide", "artritis_reumatoide"),
    ("fibromialgia", "fibromialgia"),
    ("artrosis", "artrosis"),
    ("cardiopatia", "cardiopatia"),
    ("cardiopatias", "cardiopatia"),
    ("asma", "asma"),
    ("alergia", "alergia"),
    ("cancer", "cancer"),
    ("hipotiroidismo", "hipotiroidismo"),
    ("tiroides", "tiroides"),
    ("diabetes", "diabetes"),
    ("espondilitis", "espondilitis_anquilosante"),
    ("hta", "hipertension"),
    ("tension alta", "hipertension"),
]


NONE_PATTERNS = {
    "",
    "nada",
    "ninguna",
    "ninguno",
    "no",
    "que se sepa ninguna",
    "que se sepa ninguna.",
}


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)

    rows = read_source()
    public_rows = []
    private_rows = []

    for index, row in enumerate(rows, start=1):
        cleaned = clean_row(row, index)
        public_rows.append({field: cleaned[field] for field in PUBLIC_FIELDS})
        private_rows.append({field: cleaned[field] for field in PRIVATE_FIELDS})

    write_csv(PUBLIC_OUTPUT, PUBLIC_FIELDS, public_rows)
    write_csv(PRIVATE_OUTPUT, PRIVATE_FIELDS, private_rows)
    write_report(rows, public_rows, private_rows)

    print(f"OK: {len(rows)} respuestas limpiadas")
    print(f"Publico: {PUBLIC_OUTPUT}")
    print(f"Privado: {PRIVATE_OUTPUT}")
    print(f"Informe: {REPORT_OUTPUT}")


def read_source() -> list[dict[str, str]]:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"No existe el CSV origen: {SOURCE_PATH}")
    with SOURCE_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def clean_row(row: dict[str, str], index: int) -> dict[str, str]:
    notes = []
    birthdate, age, birth_note = clean_birthdate(value(row, "Cumpleaños"))
    if birth_note:
        notes.append(birth_note)

    weight = clean_decimal(value(row, "Peso CON COMA"))
    height_m = clean_decimal(value(row, "Altura CON COMA"))
    height_cm = round(height_m * 100, 1) if height_m else ""
    bmi = round(weight / (height_m**2), 1) if weight and height_m else ""

    if not birthdate:
        notes.append("birthdate_invalid_or_missing")
    if not weight:
        notes.append("weight_missing")
    if not height_m:
        notes.append("height_missing")

    diseases_raw = value(row, "Enfermedades")
    diseases = clean_diseases(diseases_raw)
    medication_raw = value(row, "Medicación")
    medication = clean_medication(medication_raw)

    username = f"survey_{index:03d}"
    gender = clean_gender(value(row, "Género"))
    first_name, last_name = fake_identity(index, gender)
    original_first_name = clean_name(value(row, "Nombre"))
    original_last_name = clean_name(value(row, "Apellidos"))

    return {
        "participant_id": f"P{index:03d}",
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "age_group": age_group(age),
        "birthdate": birthdate.isoformat() if birthdate else "",
        "age": age or "",
        "gender": gender,
        "province": clean_name(value(row, "Provincia")),
        "weight_kg": format_decimal(weight),
        "height_cm": format_decimal(height_cm),
        "height_m": format_decimal(height_m),
        "bmi": format_decimal(bmi),
        "level": clean_level(value(row, "Nivel")),
        "objective": clean_objective(value(row, "Objetivo")),
        "diseases_standardized": "|".join(diseases),
        "medication_standardized": medication,
        "objective_raw": value(row, "Objetivo"),
        "has_disease": bool_to_text(bool(diseases)),
        "disease_count": len(diseases),
        "has_medication": bool_to_text(not is_none_text(medication_raw)),
        "source_timestamp": normalize_spaces(value(row, "Marca temporal")),
        "quality_notes": ";".join(notes),
        "original_first_name": original_first_name,
        "original_last_name": original_last_name,
        "diseases_raw": diseases_raw,
        "medication_standardized": medication,
        "medication_raw": medication_raw,
    }


def value(row: dict[str, str], key: str) -> str:
    return normalize_spaces(row.get(key, ""))


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\u202f", " ").replace("\xa0", " ")).strip()


def normalize_key(text: str) -> str:
    text = normalize_spaces(text).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def clean_name(text: str) -> str:
    text = normalize_spaces(text)
    return " ".join(part.capitalize() for part in text.split())


def fake_identity(index: int, gender: str) -> tuple[str, str]:
    position = index - 1
    first_names = FAKE_FIRST_NAMES_BY_GENDER.get(gender, FAKE_FIRST_NAMES_BY_GENDER["otro"])
    return first_names[position % len(first_names)], FAKE_LAST_NAMES[position % len(FAKE_LAST_NAMES)]


def clean_decimal(text: str) -> float | None:
    text = normalize_spaces(text).replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def clean_birthdate(text: str) -> tuple[date | None, int | None, str | None]:
    text = normalize_spaces(text)
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return None, None, "birthdate_parse_error"

    note = None
    if 0 < parsed.year < 100:
        parsed = parsed.replace(year=1900 + parsed.year)
        note = "birthdate_year_corrected"

    age = TODAY.year - parsed.year - ((TODAY.month, TODAY.day) < (parsed.month, parsed.day))
    if parsed > TODAY or age < 14 or age > 90:
        return None, None, "birthdate_out_of_range"

    return parsed, age, note


def clean_gender(text: str) -> str:
    key = normalize_key(text)
    if key.startswith("h"):
        return "hombre"
    if key.startswith("m"):
        return "mujer"
    return "otro"


def age_group(age: int | None) -> str:
    if not age:
        return ""
    lower = (age // 10) * 10
    upper = lower + 9
    return f"{lower}-{upper}"


def clean_level(text: str) -> str:
    key = normalize_key(text)
    if "avanz" in key:
        return "avanzado"
    if "medio" in key or "intermedio" in key:
        return "intermedio"
    return "principiante"


def clean_objective(text: str) -> str:
    key = normalize_key(text)
    if any(token in key for token in ["perder", "peder", "peso"]):
        return "perdida_grasa"
    if any(token in key for token in ["ganar", "muscul", "fortalecer", "fuerte", "juerte", "empeta"]):
        return "fuerza"
    if any(token in key for token in ["resistencia"]):
        return "resistencia"
    return "mantenimiento"


def is_none_text(text: str) -> bool:
    return normalize_key(text) in NONE_PATTERNS


def clean_diseases(text: str) -> list[str]:
    if is_none_text(text):
        return []

    key = normalize_key(text)
    found = []
    for needle, disease in DISEASE_KEYWORDS:
        if needle in key and disease not in found:
            found.append(disease)

    return found or ["otra"]


def clean_medication(text: str) -> str:
    if is_none_text(text):
        return ""

    key = normalize_key(text)
    categories = []
    medication_rules = [
        (["azatioprina", "infliximab"], "inmunosupresor"),
        (["eutirox", "tiroides"], "tratamiento_tiroides"),
        (["metformina"], "antidiabetico"),
        (["quimioterapia"], "tratamiento_oncologico"),
        (["bisoporol", "tension", "colesterol", "acetalidilico"], "tratamiento_cardiovascular"),
        (["anticoncept"], "tratamiento_hormonal"),
        (["ebastina", "alergia"], "tratamiento_alergia"),
        (["circulacion"], "tratamiento_circulatorio"),
        (["adenuric"], "tratamiento_metabolico"),
        (["xeristar"], "tratamiento_cronico_no_especificado"),
        (["si"], "medicacion_no_especificada"),
    ]

    for needles, category in medication_rules:
        if any(needle in key for needle in needles) and category not in categories:
            categories.append(category)

    return "|".join(categories or ["medicacion_no_especificada"])


def clean_free_text(text: str) -> str:
    if is_none_text(text):
        return ""
    return normalize_spaces(text).lower()


def format_decimal(value_: float | str | None) -> str:
    if value_ in (None, ""):
        return ""
    return f"{float(value_):.2f}"


def bool_to_text(value_: bool) -> str:
    return "true" if value_ else "false"


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(raw_rows: list[dict[str, str]], public_rows: list[dict[str, str]], private_rows: list[dict[str, str]]) -> None:
    objectives = Counter(row["objective"] for row in public_rows)
    levels = Counter(row["level"] for row in public_rows)
    genders = Counter(row["gender"] for row in public_rows)
    provinces = Counter(row["province"] for row in public_rows)
    invalid_birthdates = sum(1 for row in public_rows if "birthdate" in row["quality_notes"])
    with REPORT_OUTPUT.open("w", encoding="utf-8") as file:
        file.write("# Informe de limpieza de encuesta\n\n")
        file.write(f"- Respuestas origen: {len(raw_rows)}\n")
        file.write(f"- Registros publicos anonimizados: {len(public_rows)}\n")
        file.write(f"- Registros sensibles locales: {len(private_rows)}\n")
        file.write(f"- Fechas de nacimiento invalidas o corregidas: {invalid_birthdates}\n")
        file.write("- Salida publica: `data/processed/survey_profiles_clean.csv`\n")
        file.write("- Salida privada ignorada por Git: `data/private/survey_profiles_sensitive.csv`\n\n")
        write_counter(file, "Objetivos normalizados", objectives)
        write_counter(file, "Niveles normalizados", levels)
        write_counter(file, "Generos normalizados", genders)
        write_counter(file, "Provincias", provinces)
        file.write("\n## Reglas principales\n\n")
        file.write("- Los nombres y apellidos del dataset publico son ficticios.\n")
        file.write("- Se eliminan nombres reales, apellidos reales, fecha de nacimiento exacta, timestamp y datos sanitarios crudos del dataset publico.\n")
        file.write("- Los participantes se renombran como `P001`, `P002`, etc.\n")
        file.write("- La edad exacta se agrupa por decadas en el dataset publico.\n")
        file.write("- Pesos y alturas pasan de coma decimal a punto decimal.\n")
        file.write("- Altura se guarda en metros y centimetros.\n")
        file.write("- `Medio` se normaliza como `intermedio`.\n")
        file.write("- Objetivos libres se agrupan en `perdida_grasa`, `fuerza`, `resistencia` o `mantenimiento`.\n")
        file.write("- Enfermedades y medicacion se publican solo como categorias estandarizadas.\n")


def write_counter(file, title: str, counter: Counter) -> None:
    file.write(f"\n## {title}\n\n")
    for key, count in counter.most_common():
        file.write(f"- {key}: {count}\n")


if __name__ == "__main__":
    main()
