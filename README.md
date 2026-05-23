# P3 - Zeta Banco Onboarding OCR | Grupo Azeta

## ① Objetivo de negocio

**Problema:** Zeta Banco procesa 500+ aperturas de cuenta al mes. Cada verificacion manual de documentos toma 20 minutos, con tasa de error humano del 3%.

**Solucion:** API en Python/FastAPI que recibe imagen de cedula, ejecuta OCR (Tesseract + OpenCV), extrae campos estructurados, y valida autenticidad con Claude. Score de confianza 0-100 con umbral configurable.

## ② Arquitectura

```
POST /api/ocr (multipart: document)
    |
    v
OpenCV: preprocess (grayscale, threshold, deskew)
    |
    v
Tesseract: extract_text (--psm 3 -l spa)
    |
    v
Regex: parse_cedula_fields (cedula, nombre, fecha, direccion)
    |
    v
Confidence scoring (weighted: cedula 40%, nombre 30%, fecha 15%, dir 15%)
    |
    v (opcional: validate=true)
Claude 3 Haiku: validacion semantica de campos
    |
    v
JSON Response: { success, confidence, fields, validation }
```

## ③ Por que Python y no JS para OCR

- **OpenCV + Tesseract** son librerias nativas de Python. No existen bindings maduros en Node.js.
- **FastAPI** es el equivalente a Next.js API Routes en Python: async, automatic OpenAPI docs, validacion Pydantic.
- **Separacion de concerns**: el OCR es un microservicio independiente. Los proyectos JS (P1, P2, P4) pueden llamarlo via HTTP.

## ④ Preprocesamiento de imagen

El preprocesamiento es el 80% de la precision del OCR:

1. **Grayscale**: Elimina ruido de color.
2. **Adaptive Threshold**: Binariza la imagen considerando iluminacion local (fotos con flash, sombras).
3. **Deskew**: Corrige la inclinacion de la foto (el usuario no siempre toma la foto perfectamente alineada).

## ⑤ Validacion con Claude

**Por que validar con IA en vez de solo regex:**
- El OCR puede confundir "0" con "O", "1" con "l", "S" con "5".
- Claude detecta si un nombre "extraido" es realmente un nombre o ruido (ej: "CÉDÜLA DE" no es un nombre valido).
- Costo bajo: Claude 3 Haiku cuesta ~$0.25/1M tokens. Cada validacion usa ~200 tokens = $0.00005 por solicitud.

**Por que no usar OpenAI para esto:**
- Claude es mejor en tareas de validacion estructurada (segun benchmarks internos).
- Pero el codigo usa `anthropic` SDK, que se puede cambiar a OpenAI facilmente.

## ⑥ Variables de entorno

```
ANTHROPIC_API_KEY=your-anthropic-api-key
TESSERACT_CMD=tesseract
CONFIDENCE_THRESHOLD=70
```

## ⑦ Deploy

```bash
# Local
cd P3-onboarding-ocr
pip install -r requirements.txt
# Instalar Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
uvicorn app.main:app --reload --port 8000

# Docker
docker build -t onboarding-ocr .
docker run -p 8000:8000 --env-file .env onboarding-ocr
```

## ⑧ Argumentos de entrevista

**Impacto en Zeta Banco:**
- Reduce tiempo de verificacion de 20 min a <5 segundos.
- Score de confianza permite automatizar el 70% de las verificaciones (solo las de baja confianza van a revision manual).
- Tasa de error baja de 3% (humano) a <0.5% (OCR + validacion IA).

**Por que OCR tradicional + IA y no solo IA multimodal:**
- GPT-4o con vision podria extraer los campos, pero costo $5/1M tokens vs $0 practicamente de Tesseract.
- Tesseract extrae el texto crudo (gratis, local), Claude solo valida (~$0.00005/solicitud).
- La combinacion es 100x mas barata que usar solo vision API.
