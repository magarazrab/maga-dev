import { serve } from 'https://deno.land/std@0.224.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
serve(async (req) => {
  const token = req.headers.get('authorization')?.replace('Bearer ', '');
  if (token !== Deno.env.get('REVENUECAT_WEBHOOK_AUTH_TOKEN')) return new Response('Unauthorized', { status: 401 });
  const event = await req.json();
  const supabase = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
  const appUserId = event.event?.app_user_id;
  const entitlement = event.event?.entitlement_id;
  const status = event.event?.type;
  if (!appUserId || !entitlement) return new Response('Ignored', { status: 202 });
  const plan = entitlement === 'ultra' ? 'ultra' : entitlement === 'pro' ? 'pro' : 'free';
  await supabase.from('subscriptions').insert({ user_id: appUserId, revenuecat_app_user_id: appUserId, entitlement, status, raw_event: event });
  await supabase.from('profiles').update({ plan, updated_at: new Date().toISOString() }).eq('id', appUserId);
  return Response.json({ ok: true });
});
