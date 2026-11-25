# Magnetix Furniture website

Static site (Armenian, Russian, English) for magnetix.am, hosted on Render as a free static site.

- `public/` is the live site. Render serves it as-is (see `render.yaml`).
- `public/img/<chair>/` holds each chair's photos (front, side, semi + 3 interiors), exported from the Mac `Models/` folders.
- `assets/items.json` is the chair list (code, price, stock). It comes only from the stock sheet and folder names, never buyer data.
- To change texts, prices or chairs: edit `build.py` or `assets/items.json`, run `python3 build.py` (needs Pillow), commit.
