# Documentos FitBit

Carpeta de documentacion, memoria, analisis exploratorio, presentacion y video final del proyecto FitBit.

Esta carpeta forma parte del proyecto principal y debe vivir dentro de:

```text
FitBit/documentos_fitbit/
```

## Contenido

```text
documentos_fitbit/
|-- assets/
|   |-- arquitectura_fitbit.png
|   |-- chart_actividad_objetivo.png
|   |-- chart_objetivos.png
|   `-- evolve_logo.png
|-- data/
|   |-- dataset.csv
|   `-- dataset_clean.csv
|-- notebooks/
|   `-- eda.ipynb
|-- memoria_fitbit.docx
|-- presentacion_fitbit.pptx
|-- Video_Presentacion_TFM.mp4
|-- README.md
`-- requirements.txt
```

## Entrega audiovisual

La presentacion y el video final estan orientados a defender el producto como MVP funcional:

```text
presentacion_fitbit.pptx
Video_Presentacion_TFM.mp4
```

La estructura seguida es:

- Problema y oportunidad.
- Usuario objetivo.
- Solucion FitBit.
- Demo funcional.
- Valor del producto.
- Datos y confianza.
- Potencial de crecimiento.
- Cierre comercial.

## Memoria

La memoria principal del proyecto esta en:

```text
memoria_fitbit.docx
```

Incluye introduccion, objetivos, alcance del MVP, fuentes de datos, arquitectura, modelo de datos, recomendador, frontend/backend, EDA, planificacion, seguridad, resultados, limitaciones y conclusiones.

## EDA

El notebook de analisis exploratorio esta en:

```text
notebooks/eda.ipynb
```

El dataset principal del EDA esta en:

```text
data/dataset.csv
```

Para ejecutar el EDA:

```powershell
cd D:\Evolve\TFM\FitBit
pip install -r documentos_fitbit\requirements.txt
jupyter notebook documentos_fitbit\notebooks\eda.ipynb
```

## Nota de privacidad

Esta carpeta contiene datasets anonimizados y documentacion del proyecto. No se debe incluir aqui el CSV original de encuesta si contiene nombres reales, fechas exactas o datos sanitarios sin anonimizar.
