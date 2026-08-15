# Nebula Cut Mobile Studio

Nebula Cut is a mobile-first cosmic video editor architecture built with TypeScript, Supabase, RevenueCat entitlements, and a real timeline mutation/export-planning core. The existing Telegram bot remains in the repository, while the new editor code lives under `app/`.

## Project structure

- `app/editor` — real timeline operations: create projects, add tracks/clips, trim, split, move, duplicate, delete, and mutate clip properties.
- `app/export` — export validation and FFmpeg argument planning for MP4 output tiers.
- `app/subscription` — Free/Pro/Ultra feature gates and RevenueCat entitlement mapping.
- `app/services` — Supabase and AI service adapters that require environment variables instead of hard-coded secrets.
- `app/config` — filter, transition, and effect catalogs.
- `supabase/migrations` — PostgreSQL schema, RLS policies, and private storage buckets.
- `supabase/functions` — secure RevenueCat webhook and first-admin bootstrap Edge Functions.

## Environment variables

Copy `.env.example` and fill in real values. Never commit secrets.

- `EXPO_PUBLIC_SUPABASE_URL`
- `EXPO_PUBLIC_SUPABASE_ANON_KEY`
- `EXPO_PUBLIC_REVENUECAT_API_KEY`
- `REVENUECAT_PROJECT_ID`
- `REVENUECAT_WEBHOOK_AUTH_TOKEN`
- `SUPABASE_SERVICE_ROLE_KEY`
- `AI_API_BASE_URL`
- `AI_API_KEY`
- `ADMIN_BOOTSTRAP_LOGIN`
- `ADMIN_BOOTSTRAP_PASSWORD`

## Supabase setup

1. Create a Supabase project.
2. Run `supabase db push` from this repository.
3. Deploy functions with `supabase functions deploy revenuecat-webhook` and `supabase functions deploy admin-bootstrap`.
4. Configure Edge Function secrets for service-role, RevenueCat webhook token, and admin bootstrap password.
5. Invoke `admin-bootstrap` once with the bootstrap login/password; the password is handled by Supabase Auth and is never stored in client code.

## RevenueCat setup

Create products `PRO_MONTHLY`, `PRO_YEARLY`, `ULTRA_MONTHLY`, and `ULTRA_YEARLY`, then create entitlements `pro` and `ultra`. Point the RevenueCat webhook at the deployed `revenuecat-webhook` function and use `REVENUECAT_WEBHOOK_AUTH_TOKEN` as the bearer token.

## What works now

- Timeline data model with multiple track kinds.
- Real clip operations: trim, split, move, duplicate, delete, property updates.
- Free/Pro/Ultra access-control logic sourced from RevenueCat entitlements.
- Export setting validation and deterministic FFmpeg argument planning.
- Supabase schema with profiles, projects, files, subscriptions, settings, exports, usage, admin logs, RLS, and private storage buckets.
- Secure server-side bootstrap path for the initial administrator.
- AI tool service layer that refuses to run until configured with a backend API.

## Requires native/API integration next

- React Native/Expo screens and native media permissions.
- Native FFmpeg execution module for on-device rendering.
- RevenueCat SDK initialization in the mobile shell.
- Supabase Auth UI providers for Google/Apple.
- External AI APIs for captions, background removal, smart cut, and beat sync.

## Development

```bash
npm install
npm run typecheck
npm run lint
npm run build
```

For the existing Telegram bot:

```bash
python -m py_compile bot.py database.py
```
