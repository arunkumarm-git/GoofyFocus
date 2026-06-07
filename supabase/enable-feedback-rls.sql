-- SQL Script to enable Row Level Security on public.feedback
-- Run this script in the Supabase Dashboard SQL Editor (https://supabase.com/dashboard/project/_/sql)

-- 1. Enable Row Level Security (RLS) on the feedback table
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

-- 2. Clean up any existing insertion policies to avoid duplicate name conflicts
DROP POLICY IF EXISTS "Allow anonymous feedback insertion" ON public.feedback;

-- 3. Create a policy that allows anyone (signed-in or anonymous users using the anon client key) to insert feedback
CREATE POLICY "Allow anonymous feedback insertion" ON public.feedback
  FOR INSERT 
  TO anon, authenticated
  WITH CHECK (true);

-- Note: Because we have only specified an INSERT policy, select, update, and delete actions
-- will be blocked by default for non-admin/non-service-role clients, maintaining privacy.
