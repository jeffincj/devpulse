# DevPulse — Real-Time Developer Productivity & Sprint Analytics API

A Django REST Framework backend that pulls **live data from the GitHub API**
(pull requests, reviews, commits) and computes real engineering metrics:
sprint velocity, PR review turnaround, code churn, and contributor activity.

Built and tested end-to-end (JWT auth → team creation → repo linking →
GitHub sync → metrics) before being handed to you — every endpoint below has
actually been exercised with real `curl` calls against real GitHub data.

---

## 1. Project layout

```
devpulse_build/
├── manage.py
├── requirements.txt
├── .env.example              # copy to .env and fill in your values
├── Dockerfile
├── docker-compose.yml
├── devpulse_project/         # Django project (settings, root urls)
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                 # Custom auth: JWT login/register + roles
│   ├── models.py             # Profile(role: manager/developer)
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── teams/                    # Teams, memberships, sprints
│   ├── models.py             # Team, Membership, Sprint
│   ├── permissions.py        # IsManager, IsTeamManagerOrReadOnly
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── github_integration/       # The GitHub API integration
│   ├── models.py             # Repository, PullRequest, Commit
│   ├── services.py           # GitHubClient + sync_repository()
│   ├── management/commands/sync_github_data.py   # CLI sync command
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
└── metrics/                  # Aggregation / analytics endpoints
    ├── services.py           # velocity, turnaround, churn, activity
    ├── views.py
    └── urls.py
```

---

## 2. How it was built (in case you want to recreate it yourself)

If you want to reproduce this from scratch instead of using the files
directly, this is the exact sequence:

```bash
mkdir devpulse && cd devpulse
python -m venv venv && source venv/bin/activate

pip install django djangorestframework djangorestframework-simplejwt \
            django-filter drf-spectacular requests python-dotenv \
            psycopg2-binary gunicorn

django-admin startproject devpulse_project .
python manage.py startapp accounts
python manage.py startapp teams
python manage.py startapp github_integration
python manage.py startapp metrics
```

Then you'd create each file shown in the folder tree above (all provided for
you already), register the 4 apps + the 3rd-party packages in
`INSTALLED_APPS`, wire up `urls.py`, and run:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Since every file is already written for you in this project, **you can skip
straight to step 3 below.**

---

## 3. Running it yourself

### Option A — Local (SQLite, fastest way to try it)

```bash
cd devpulse_build
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# open .env and paste a GitHub personal access token (Settings -> Developer
# settings -> Personal access tokens -> generate one with just "repo" read
# scope, or no scope at all for public repos). Leave DB_NAME blank to use
# SQLite automatically.

python manage.py makemigrations accounts teams github_integration
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API is now live at `http://127.0.0.1:8000/`.
Interactive Swagger docs: `http://127.0.0.1:8000/api/docs/`

### Option B — Docker (Postgres, production-like)

```bash
cp .env.example .env
# fill in GITHUB_TOKEN, and set DB_NAME=devpulse (matches docker-compose.yml)
docker compose up --build
```

This spins up Postgres + the Django app together, runs migrations
automatically, and serves via Gunicorn on `http://localhost:8000/`.

---

## 4. Why a GitHub token?

Unauthenticated GitHub API requests are capped at 60/hour and shared across
your whole network — a single `sync` on an active repo will burn through
that fast. A personal access token raises it to 5,000/hour. Generate one at
**github.com → Settings → Developer settings → Personal access tokens →
Fine-grained tokens**, give it read-only access to the repos you want to
track, and paste it into `.env` as `GITHUB_TOKEN`.

---

## 5. Walking through the API

All endpoints below were tested live during development. Replace
`<TOKEN>` with the `access` token from the login response.

### 5.1 Register + log in

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"priya_manager","email":"priya@example.com","password":"StrongPass123","role":"manager"}'

curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"priya_manager","password":"StrongPass123"}'
# -> {"refresh": "...", "access": "..."}
```

`role` can be `"manager"` or `"developer"` — this drives the permission
checks on team/repo write operations (`IsTeamManagerOrReadOnly`).

### 5.2 Create a team (you become its manager automatically)

```bash
curl -X POST http://127.0.0.1:8000/api/teams/ \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"name":"Payments Squad","description":"Owns checkout + payouts"}'
```

Add a developer to it:

```bash
curl -X POST http://127.0.0.1:8000/api/teams/1/add-member/ \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"username":"some_dev","role":"developer"}'
```

### 5.3 Link a GitHub repository to the team

```bash
curl -X POST http://127.0.0.1:8000/api/repositories/ \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"team": 1, "full_name": "psf/requests"}'
```

### 5.4 Sync live data from GitHub

```bash
curl -X POST http://127.0.0.1:8000/api/repositories/1/sync/ \
  -H "Authorization: Bearer <TOKEN>"
```

This pulls PRs (with additions/deletions/first-review-time) and commits from
GitHub and upserts them into the DB. You can also run it from the CLI for
all repos, or one repo, at once — handy for a cron job:

```bash
python manage.py sync_github_data                       # all repos
python manage.py sync_github_data --repo psf/requests    # just one
```

### 5.5 Read the analytics

```bash
# Merged PRs + lines merged in a date window (velocity proxy)
curl "http://127.0.0.1:8000/api/metrics/velocity/?team_id=1&start_date=2026-07-01&end_date=2026-07-21" \
  -H "Authorization: Bearer <TOKEN>"

# Average hours between PR open and first review, last 30 days
curl "http://127.0.0.1:8000/api/metrics/pr-turnaround/?repository_id=1&days=30" \
  -H "Authorization: Bearer <TOKEN>"

# Lines added/removed/net churn on merged PRs, last 30 days
curl "http://127.0.0.1:8000/api/metrics/code-churn/?repository_id=1&days=30" \
  -H "Authorization: Bearer <TOKEN>"

# Commits + merged PRs per contributor across the team's repos
curl "http://127.0.0.1:8000/api/metrics/contributor-activity/?team_id=1&days=30" \
  -H "Authorization: Bearer <TOKEN>"

# Open PRs nobody has reviewed yet
curl "http://127.0.0.1:8000/api/pull-requests/pending-review/?repository=1" \
  -H "Authorization: Bearer <TOKEN>"
```

All list endpoints (`/api/pull-requests/`, `/api/commits/`, `/api/teams/`,
`/api/repositories/`) support pagination, and filtering via query params
(e.g. `?state=merged&author_username=octocat`), plus `?search=` and
`?ordering=` — all wired through `django-filter` + DRF's built-in backends,
not hand-rolled.

---

## 6. Design notes worth mentioning in an interview

- **Metrics are computed at the DB level** (`Sum`, `Count`, annotated
  querysets in `metrics/services.py`), not looped over in Python — this is
  the difference between a CRUD app and something that scales.
- **Velocity is a deliberate proxy.** Without a connected ticketing system
  (Jira/Linear), "story points" don't exist — so velocity here is merged-PR
  count + lines merged in a window. That's a defensible, explainable choice,
  and swapping in a real ticket-count source later is a one-function change
  in `metrics/services.py`.
- **Role-based permissions are enforced at the object level**
  (`teams/permissions.py`), not just "is authenticated" — a developer can
  read a team's data but not rename it or add/remove members.
- **The GitHub sync is idempotent** (`update_or_create` keyed on
  `(repository, number)` / `(repository, sha)`), so re-running it is always
  safe and only touches what changed.
- **Swagger/OpenAPI docs are auto-generated** from the actual serializers
  and viewsets via `drf-spectacular` — `/api/docs/` always matches the code,
  it's never hand-written and never goes stale.
