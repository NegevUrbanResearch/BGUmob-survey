# BGU Mobility Survey Dashboard

Interactive visualization platform for analyzing student transportation patterns around Ben-Gurion University (BGU) campus collected via submissions through ZenCity Surveys.

## Project overview

This site presents campus mobility insights collected from BGU students to understand the relationship between the university and the city:

- Students' modes of travel to and from campus
- Common routes and entry gates
- Amenities students engage with along the way

### Supabase config for Feedback

We save feedback (optional email) to a Supabase table `feedback` via the anon key. Enable Row Level Security (RLS) with insert-only policies.

For local:

1. Copy `config.example.js` to `config.js`
2. Fill `window.SUPABASE_URL` and `window.SUPABASE_ANON_KEY`

Table and policies (run in Supabase SQL editor):

```sql
create table if not exists feedback (
  id uuid primary key default gen_random_uuid(),
  note text not null,
  email text,
  created_at timestamptz not null default now()
);

alter table feedback enable row level security;

create policy feedback_insert_anon
  on feedback for insert
  to anon, authenticated
  with check (true);
```

## Deployment (GitHub Pages)

We deploy with GitHub Actions, injecting `config.js` from repository secrets to keep the anon key out of the repo.

1. Add secrets in repo Settings → Secrets and variables → Actions

- `SUPABASE_URL` = your project URL
- `SUPABASE_ANON_KEY` = your anon key

2. Provided workflow `.github/workflows/deploy.yml` does:

- Creates `config.js` from those secrets
- Uploads artifact and deploys to GitHub Pages

3. Ensure repository Pages is enabled (Settings → Pages)

## Local development

Prerequisites:

- Node.js ≥ 14 (for npm scripts) and Python ≥ 3.8 (for the default static server)
- The `outputs/` directory present with the generated data and charts

Setup:

1. Copy `config.example.js` to `config.js`
2. Set your Supabase values in `config.js`:
   - `window.SUPABASE_URL = 'https://YOUR-PROJECT.supabase.co'`
   - `window.SUPABASE_ANON_KEY = 'YOUR-ANON-KEY'`

Run locally:

- Start a local static server:
  - `npm start` (uses `python3 -m http.server 8000`)
  - or `npm run serve`
  - or `npx http-server -p 8000`
- Open `http://localhost:8000`

Testing feedback submission:

- Ensure the `feedback` table exists and RLS insert policy is enabled (see above)
- Enter a comment (and optional email) in the Info modal → Comments → Send Feedback
- If Supabase is not configured or fails, an error is shown and the note is not sent

## Directory structure

- `index.html` — main app and UI
- `assets/js/map-controller.js` — MapLibre/deck.gl logic
- `outputs/` — precomputed data and charts (HTML/JSON)
- `config.example.js` — sample client config; copy to `config.js`
- `config.js` — injected at deploy (ignored by git)
