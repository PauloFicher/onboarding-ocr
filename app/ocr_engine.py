"""
OCR Processing Engine
Extrae datos estructurados de una cedula paraguaya.

Flujo:
1. Preprocesar imagen (OpenCV: grayscale, threshold, deskew)
2. OCR con Tesseract (configurado para espanol)
3. Extraer campos con regex + validacion estructural
4. Validar semantica con Claude (opcional, mejora precision)
"""
import re
import os
import io
import json
from typing import Optional
import cv2
import numpy as np
from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Convertir a escala de grises, binarizar y corregir inclinacion."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = thresh.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        thresh = cv2.warpAffine(
            thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

    return thresh


def extract_text(image: np.ndarray) -> str:
    """OCR con Tesseract configurado para espanol."""
    pil_img = Image.fromarray(image)
    config = "--psm 3 -l spa --oem 3"
    return pytesseract.image_to_string(pil_img, config=config)


def parse_cedula_fields(text: str) -> dict:
    """Extraer campos especificos de cedula paraguaya usando regex."""
    text_clean = text.strip()

    cedula_match = re.search(r"\b(\d{1,3}\.\d{3}\.\d{3})\b", text_clean)
    cedula = cedula_match.group(1).replace(".", "") if cedula_match else None

    nombre_match = re.search(
        r"(?:NOMBRES?\s*(?:Y\s*APELLIDOS?)?\s*[:\-\s]+|APELLIDOS?\s*(?:Y\s*NOMBRES?)?\s*[:\-\s]+)([A-ZÁÉÍÓÚÑ\s]{5,60})",
        text_clean,
        re.IGNORECASE,
    )
    nombre = nombre_match.group(1).strip() if nombre_match else None

    fecha_match = re.search(
        r"(?:FECHA\s*DE\s*NACIMIENTO|NACIDO?)\s*[:\-\s]*(\d{1,2}\s*(?:de\s*)?\w+\s*(?:de\s*)?\d{4})",
        text_clean,
        re.IGNORECASE,
    )
    fecha_nac = fecha_match.group(1).strip() if fecha_match else None

    direccion_match = re.search(
        r"(?:DIRECCI[OÓ]N|DOMICILIO)\s*[:\-\s]*(.+?)(?:\n|\s{2,}|$)", text_clean, re.IGNORECASE
    )
    direccion = direccion_match.group(1).strip() if direccion_match else None

    return {
        "cedula": cedula,
        "nombre": nombre,
        "fecha_nacimiento": fecha_nac,
        "direccion": direccion,
        "raw_text": text_clean[:500],
    }


def compute_confidence(fields: dict) -> int:
    """
    Score de confianza 0-100 basado en cuantos campos se extrajeron.
    """
    weights = {"cedula": 40, "nombre": 30, "fecha_nacimiento": 15, "direccion": 15}
    score = 0
    for field, weight in weights.items():
        if fields.get(field):
            score += weight

    # Penalizar si el texto raw es muy corto o parece ruido
    raw = fields.get("raw_text", "")
    if len(raw) < 50:
        score = min(score, 30)

    return score
