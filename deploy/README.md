# Deploying Crystal

The site and the dashboard run on the client's own Hostinger VPS
(`187.126.118.190`, Ubuntu 24.04). The static site is served by nginx straight
off `/var/www/crystal`; `/admin` and `/api` are proxied to gunicorn.

## Pushing a change

Push to `main` and wait up to five minutes — a systemd timer checks GitHub and
deploys when `origin/main` has moved. To go now instead:

    ssh root@187.126.118.190 /root/deploy.sh

## Stopping auto-deploy without disabling it

During a DNS cutover, or any time the server must not change under you:

    ssh root@187.126.118.190 touch /root/HOLD-DEPLOY     # pause
    ssh root@187.126.118.190 rm /root/HOLD-DEPLOY        # resume

The timer keeps ticking and keeps logging that it is holding, so a forgotten
hold is visible rather than silent.

## The scripts

| file | what it does |
|---|---|
| `vps-setup.sh` | builds the box from bare Ubuntu. Idempotent. Never touches DNS or certificates. |
| `vps-deploy.sh` | fetch, re-chown, pip, migrate, sync catalogue, collectstatic, restart, then verify `/api/products/` answers 200 before reporting success. |
| `vps-autodeploy.sh` | deploys only when `origin/main` has moved; what the timer runs. |

## Two things that will bite you

**Ownership.** `MEDIA_ROOT` is the repo root on this server — that is deliberate,
so a dashboard upload lands where the static site can serve it. But git runs as
root and gunicorn as `www-data`, so a plain `git pull` leaves the tree
unwritable and **every save in the dashboard 500s**. `vps-deploy.sh` re-chowns
on every run; if you ever pull by hand, do the same.

**nginx location order.** `/media/` must be `location ^~ /media/`. A plain
prefix location loses to the image regex block, because nginx matches regex
locations first, and every uploaded image 404s.

## Logs

    journalctl -u crystal -n 50          # the Django app
    tail -f /var/log/crystal-autodeploy.log
    tail -f /var/log/nginx/access.log
