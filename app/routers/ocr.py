"""
API Router para el endpoint de onboarding OCR.

POST /api/ocr
  - Recibe: archivo de imagen (multipart/form-data, campo "document")
  - Devuelve: campos extraidos + confidence score + validacion

POST /api/ocr/validate
  - Recibe: campos extraidos (JSON)
  - Devuelve: validacion de autenticidad via Claude
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from app.ocr_engine import preprocess_image, extract_text, parse_cedula_fields, compute_confidence
from pydantic import BaseModel
import anthropic
import os

router = APIRouter()


class OcrResponse(BaseModel):
    success: bool
    confidence: int
    fields: dict
    validation: dict | None = None
    error: str | None = None


class ValidateRequest(BaseModel):
    fields: dict


@router.post("/ocr", response_model=OcrResponse)
async def process_document(
    document: UploadFile = File(..., description="Imagen de la cedula (JPG, PNG o PDF)"),
    validate: bool = Form(False, description="Validar campos extraidos con IA"),
):
    if not document.content_type or not document.content_type.startswith("image/"):
        raise HTTPException(400, "Solo se aceptan imagenes (JPG, PNG).")

    contents = await document.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, "La imagen no puede exceder 10MB.")

    try:
        processed = preprocess_image(contents)
    except Exception as e:
        return OcrResponse(success=False, confidence=0, fields={}, error=f"Error al procesar imagen: {e}")

    text = extract_text(processed)
    fields = parse_cedula_fields(text)
    confidence = compute_confidence(fields)

    validation = None
    if validate and fields.get("nombre") and fields.get("cedula"):
        validation = await validate_fields_with_claude(fields.get("nombre", ""), fields.get("cedula", ""))

    return OcrResponse(success=confidence >= 40, confidence=confidence, fields=fields, validation=validation)


async def validate_fields_with_claude(nombre: str, cedula: str) -> dict:
    """
    Validacion semantica con Claude:
    - Verifica que el nombre extraido sea un nombre real (no ruido OCR)
    - Verifica que la cedula tenga formato paraguayo valido
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"validated": False, "reason": "Validacion IA no configurada (ANTHROPIC_API_KEY)"}

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Valida si los siguientes datos extraidos de una cedula paraguaya son coherentes.

Nombre extraido: "{nombre}"
Cedula extraida: "{cedula}"

Responde UNICAMENTE con JSON:
{{
  "nombre_valido": true/false,
  "cedula_valida": true/false,
  "nombre_corregido": "nombre corregido si aplica, sino null",
  "observaciones": "breve explicacion si algo es invalido"
}}

Reglas:
- Nombre valido: contiene al menos nombre y apellido, sin caracteres extranos
- Cedula valida: tiene entre 6 y 9 digitos (formato paraguayo)"""

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else "{}"
        import json
        return json.loads(text.replace("```json", "").replace("```", ""))
    except Exception as e:
        return {"validated": False, "reason": f"Error de validacion: {str(e)}"}


@router.post("/ocr/validate")
async def validate_document(body: ValidateRequest):
    if not body.fields.get("nombre") or not body.fields.get("cedula"):
        raise HTTPException(400, "Se requiere nombre y cedula para validacion.")

    result = await validate_fields_with_claude(
        body.fields["nombre"], body.fields["cedula"]
    )
    return JSONResponse(content=result)
