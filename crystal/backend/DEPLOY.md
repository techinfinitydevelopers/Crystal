# Deploying the dashboard to Railway

The dashboard is a Django app living in `crystal/backend`. The Railway project
currently runs only the static website; this adds the dashboard as a second
service beside it.

Everything in the repo is already prepared. What follows is done in the Railway
dashboard, because it needs account access.

---

## 1. Add a Postgres database

In the Railway project: **New → Database → Add PostgreSQL**.

This is not optional. Without it Django falls back to a SQLite file *inside the
container*, and Railway rebuilds the container on every deploy — every product,
every edit and every password would be wiped each time you push.

Railway exposes the connection string as `DATABASE_URL`, which `settings.py`
already reads.

## 2. Add the dashboard service

**New → GitHub Repo → techinfinitydevelopers/Crystal** (the same repo the site
uses).

Then in that service's **Settings**:

| Setting | Value |
|---|---|
| Root Directory | `crystal/backend` |
| Build / Start | leave empty — `railway.toml` supplies both |

The root directory is what separates the two services: the website service
builds from the repo root, this one from `crystal/backend`.

## 3. Set the variables

In the new service's **Variables** tab:

| Variable | Value |
|---|---|
| `SECRET_KEY` | a long random string — see below |
| `DEBUG` | `False` |
| `DATABASE_URL` | reference the Postgres service (Railway offers it in the picker) |

Generate a secret key locally:

```
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

`settings.py` refuses to start with the development placeholder, so a missing or
default `SECRET_KEY` fails the deploy loudly rather than shipping a site whose
session cookies anyone can forge.

## 4. Add a volume for uploads

**Settings → Volumes → Add**, mount path `/app/media`.

Product photos and videos uploaded *through the dashboard* are written to disk.
Without a volume they share the container's fate and disappear on the next
deploy. (Images that came from `products.json` are read from the repo and are
unaffected.)

## 5. Load the catalogue

Deploy once, then open the service's **Console** and run:

```
python manage.py loaddata dashboard-seed.json
```

`dashboard-seed.json` sits in this folder and holds 5,418 records — 530
products, 2,474 images, 1,956 specifications, 317 marketplace links, 95
variants, 41 categories, 4 brands. It deliberately contains **no user
accounts**, so no password hash is stored in git.

## 6. Create your login

Still in the Console:

```
python manage.py createsuperuser
```

The dashboard is then at `https://<service-domain>/admin/`.

---

## Afterwards

**Edits still do not reach the website by themselves.** The site reads
`product-data/products.json` from the repo; the dashboard writes to Postgres.
The bridge is:

```
python manage.py export_to_json
```

then commit and push the changed `products.json`. Automating that is a separate
piece of work.

## What was changed in the repo for this

- `requirements.txt` — added `whitenoise`. With `DEBUG=False` Django serves no
  static files on its own, and `config/urls.py` only wires them up while DEBUG
  is on, so the admin would have loaded with no CSS at all.
- `config/settings.py` — WhiteNoise middleware; `CompressedStaticFilesStorage`
  (not the manifest variant, which fails a deploy outright if any stylesheet
  references a missing file, and Jazzmin ships a few); and a production block
  covering SSL redirect, secure cookies, HSTS, and `SECURE_PROXY_SSL_HEADER`.
  That last one matters: Railway terminates TLS at its edge and forwards plain
  HTTP, so without it `SECURE_SSL_REDIRECT` sends every request into a redirect
  loop. All of it is conditional on `DEBUG` being off; local development is
  unchanged.
- `Procfile` / `railway.toml` — `collectstatic` added alongside `migrate`.
