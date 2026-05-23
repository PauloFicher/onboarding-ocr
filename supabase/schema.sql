-- P3 - Onboarding OCR Schema (opcional, para guardar resultados de validacion)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS public.kyc_verifications (
  id            UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  document_type TEXT NOT NULL DEFAULT 'cedula',
  extracted_cedula TEXT,
  extracted_nombre TEXT,
  extracted_fecha_nac TEXT,
  extracted_direccion TEXT,
  confidence    INTEGER NOT NULL,
  is_validated  BOOLEAN DEFAULT false,
  validation_result JSONB,
  created_at    TIMESTAMPTZ DEFAULT now() NOT NULL
);

ALTER TABLE public.kyc_verifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_all" ON public.kyc_verifications FOR ALL TO authenticated USING (true);
