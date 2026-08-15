import { serve } from 'https://deno.land/std@0.224.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
serve(async (req) => {
  if (req.method !== 'POST') return new Response('Method not allowed', { status: 405 });
  const { login, password } = await req.json();
  if (login !== Deno.env.get('ADMIN_BOOTSTRAP_LOGIN') || password !== Deno.env.get('ADMIN_BOOTSTRAP_PASSWORD')) return new Response('Unauthorized', { status: 401 });
  const supabase = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
  const email = `${login}@admin.local`;
  const { data, error } = await supabase.auth.admin.createUser({ email, password, email_confirm: true });
  if (error && !error.message.includes('already')) return Response.json({ error: error.message }, { status: 400 });
  if (data.user) await supabase.from('profiles').upsert({ id: data.user.id, email, display_name: 'Administrator', is_admin: true });
  return Response.json({ ok: true });
});
