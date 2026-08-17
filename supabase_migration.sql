-- Supabase migration: run in SQL Editor (Dashboard → SQL → New query → Run)
-- Adds lead columns to `calls` and creates the missing `phone_numbers` table.

ALTER TABLE public.calls
  ADD COLUMN IF NOT EXISTS lead_name TEXT,
  ADD COLUMN IF NOT EXISTS lead_phone TEXT,
  ADD COLUMN IF NOT EXISTS lead_email TEXT,
  ADD COLUMN IF NOT EXISTS budget_min INTEGER,
  ADD COLUMN IF NOT EXISTS budget_max INTEGER,
  ADD COLUMN IF NOT EXISTS locations TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS bhk INTEGER,
  ADD COLUMN IF NOT EXISTS property_type TEXT,
  ADD COLUMN IF NOT EXISTS timeline TEXT,
  ADD COLUMN IF NOT EXISTS purpose TEXT,
  ADD COLUMN IF NOT EXISTS interested BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS call_summary TEXT,
  ADD COLUMN IF NOT EXISTS next_action TEXT;

CREATE TABLE IF NOT EXISTS public.phone_numbers (
  id UUID PRIMARY KEY,
  type TEXT NOT NULL,
  label TEXT NOT NULL,
  number TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.phone_numbers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow all" ON public.phone_numbers
  FOR ALL USING (true) WITH CHECK (true);

-- Dashboard login users (table may already exist — just add login columns)
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS name TEXT,
  ADD COLUMN IF NOT EXISTS password_hash TEXT;

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow all" ON public.users
  FOR ALL USING (true) WITH CHECK (true);

-- App settings (key/value, e.g. default_user_id)
CREATE TABLE IF NOT EXISTS public.settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow all" ON public.settings
  FOR ALL USING (true) WITH CHECK (true);