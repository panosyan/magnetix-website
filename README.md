# Magnetix Furniture website

Static site (Armenian, Russian, English) for magnetix.am, hosted on Render as a free static site.

- `public/` is the live site. Render serves it as-is (see `render.yaml`).
- `public/img/<chair>/` holds each chair's photos (front, side, semi + 3 interiors), exported from the Mac `Models/` folders.
- `assets/items.json` is the chair list (code, price, stock). It comes only from the stock sheet and folder names, never buyer data.
- Day to day: use the admin (Render service `magnetix-admin`, code in `admin/`). It edits `assets/items.json` and `public/img/` by committing to this repo; Render then runs `python3 build.py` and publishes `public/`.
- To change texts: edit `build.py`, run `python3 build.py` (standard library only), commit.
- Admin locally: `cd admin && pip install -r requirements.txt && LOCAL_REPO=.. ADMIN_PASSWORD=test python3 app.py`.
