"""Magnetix admin: password login, one edit page per chair, CSV / Google Sheet import and export.

Every save is a commit to the GitHub repo (assets/items.json + public/img/<slug>/*).
Render then rebuilds the public static site from the repo (about 1-2 minutes).

Environment:
  ADMIN_PASSWORD   the admin password (set in the Render dashboard)
  SECRET_KEY       random string for the login cookie (Render generates it)
  GITHUB_TOKEN     fine-grained token with Contents read/write on the repo
  GITHUB_REPO      owner/name, default panosyan/magnetix-website
  GITHUB_BRANCH    default main
  SHEET_CSV        published CSV link of the Magnetix Google Sheet (optional)
  SITE_URL         public site, default https://magnetix.onrender.com
  LOCAL_REPO       for testing: use this folder instead of GitHub (no token needed)
"""
import base64, csv, hmac, io, json, os, re, secrets, threading, time
from functools import wraps

import requests
from flask import Flask, Response, abort, flash, redirect, render_template_string, request, session, url_for
from PIL import Image, ImageOps

ITEMS = 'assets/items.json'
IMG = 'public/img'
SITE = os.environ.get('SITE_URL', 'https://magnetix.onrender.com').rstrip('/')
SHEET_CSV = os.environ.get('SHEET_CSV', '')
BADGES = [('new', 'New arrival'), ('sale', 'On sale'), ('hot', 'Hot item')]
W, H = 960, 1200

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(MAX_CONTENT_LENGTH=60 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                  SESSION_COOKIE_SECURE=not os.environ.get('LOCAL_REPO'), PERMANENT_SESSION_LIFETIME=30 * 86400)
LOCK = threading.Lock()


# ------------------------------------------------------------------ storage
class LocalStore:
    def __init__(self, root): self.root = root
    def read(self, path):
        p = os.path.join(self.root, path)
        return open(p, 'rb').read() if os.path.exists(p) else None
    def commit(self, changes, message):
        for path, data in changes.items():
            p = os.path.join(self.root, path)
            if data is None:
                if os.path.exists(p): os.remove(p)
            else:
                os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'wb').write(data)


class GitHubStore:
    API = 'https://api.github.com'
    def __init__(self, repo, branch, token):
        self.repo, self.branch = repo, branch
        self.s = requests.Session()
        self.s.headers.update({'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'magnetix-admin'})
        self.cache = {}
    def _u(self, p): return f'{self.API}/repos/{self.repo}/{p}'
    def read(self, path):
        if path in self.cache and path != ITEMS: return self.cache[path]  # chair data is always read fresh
        r = self.s.get(self._u(f'contents/{path}'), params={'ref': self.branch}, headers={'Accept': 'application/vnd.github.raw'}, timeout=30)
        if r.status_code == 404: return None
        r.raise_for_status()
        if len(self.cache) > 400: self.cache.clear()
        self.cache[path] = r.content
        return r.content
    def commit(self, changes, message):
        for attempt in range(3):
            ref = self.s.get(self._u(f'git/ref/heads/{self.branch}'), timeout=30); ref.raise_for_status()
            head = ref.json()['object']['sha']
            base = self.s.get(self._u(f'git/commits/{head}'), timeout=30).json()['tree']['sha']
            tree = []
            for path, data in changes.items():
                if data is None:
                    tree.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': None})
                else:
                    b = self.s.post(self._u('git/blobs'), json={'content': base64.b64encode(data).decode(), 'encoding': 'base64'}, timeout=60)
                    b.raise_for_status(); tree.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': b.json()['sha']})
            t = self.s.post(self._u('git/trees'), json={'base_tree': base, 'tree': tree}, timeout=60); t.raise_for_status()
            c = self.s.post(self._u('git/commits'), json={'message': message, 'tree': t.json()['sha'], 'parents': [head]}, timeout=30); c.raise_for_status()
            u = self.s.patch(self._u(f'git/refs/heads/{self.branch}'), json={'sha': c.json()['sha']}, timeout=30)
            if u.ok: break
            time.sleep(1)
        else:
            u.raise_for_status()
        for path, data in changes.items():
            if data is None: self.cache.pop(path, None)
            else: self.cache[path] = data


STORE = LocalStore(os.environ['LOCAL_REPO']) if os.environ.get('LOCAL_REPO') else \
    GitHubStore(os.environ.get('GITHUB_REPO', 'panosyan/magnetix-website'), os.environ.get('GITHUB_BRANCH', 'main'), os.environ.get('GITHUB_TOKEN', ''))


def load():
    return json.loads(STORE.read(ITEMS) or b'[]')

def save(items, message, extra=None):
    changes = dict(extra or {})
    changes[ITEMS] = (json.dumps(items, ensure_ascii=False, indent=1) + '\n').encode()
    STORE.commit(changes, message + '\n\n(saved from the Magnetix admin)')

def find(items, slug):
    for it in items:
        if it['slug'] == slug: return it
    abort(404)

def slugify(name):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', name.lower())).strip('-') or 'chair'


# ------------------------------------------------------------------ images
def make_photo(data, mode):
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert('RGB')
    if mode == 'fit':  # whole photo on white, nothing cut off
        im.thumbnail((W, H), Image.LANCZOS)
        bg = Image.new('RGB', (W, H), (255, 255, 255)); bg.paste(im, ((W - im.width) // 2, (H - im.height) // 2)); im = bg
    else:  # fill the frame, crop the edges
        im = ImageOps.fit(im, (W, H), Image.LANCZOS)
    out, small = io.BytesIO(), io.BytesIO()
    im.save(out, 'JPEG', quality=84, optimize=True, progressive=True)
    im.resize((480, 600), Image.LANCZOS).save(small, 'JPEG', quality=80, optimize=True, progressive=True)
    return out.getvalue(), small.getvalue()


# ------------------------------------------------------------------ csv
FIELDS = ['Code', 'Model', 'Price', 'Old price', 'Stock', 'Sold out', 'New arrival', 'On sale', 'Hot item', 'Hidden', 'Photos']

def yes(v): return bool(re.match(r'^\s*(y|yes|այո|да|x|1|true|✓)', str(v or ''), re.I))
def num(v):
    v = re.sub(r'[^\d]', '', str(v or '')); return int(v) if v else None

def to_csv(items):
    f = io.StringIO(); w = csv.writer(f); w.writerow(FIELDS)
    for it in items:
        b = it.get('badges') or []
        w.writerow([it['slug'], it['name'], it.get('price') or '', it.get('old_price') or '', '' if it.get('stock') is None else it['stock'],
                    'yes' if it.get('sold') else '', 'yes' if 'new' in b else '', 'yes' if 'sale' in b else '', 'yes' if 'hot' in b else '',
                    'yes' if it.get('hidden') else '', len(it.get('photos') or [])])
    return '﻿' + f.getvalue()

def apply_csv(items, text):
    """Update chairs from a CSV (ours, or the Google Sheet). Only columns present are changed. Returns (changed, unknown)."""
    rows = list(csv.reader(io.StringIO(text.lstrip('﻿'))))
    if not rows: return [], []
    head = [h.strip().lower() for h in rows[0]]
    def col(*names):
        for n in names:
            for i, h in enumerate(head):
                if h.startswith(n): return i
        return None
    ic, im, ip, io_, iq, ix = col('code'), col('model', 'name'), col('price'), col('old price', 'old'), col('stock'), col('sold')
    ib = {'new': col('new'), 'sale': col('on sale', 'sale'), 'hot': col('hot')}
    ih = col('hidden', 'hide')
    if ic is None: raise ValueError('The file needs a "Code" column (the chair code from the export).')
    by = {it['slug']: it for it in items}
    changed, unknown = [], []
    for r in rows[1:]:
        g = lambda i: r[i].strip() if i is not None and i < len(r) else None
        code = g(ic)
        if not code: continue
        it = by.get(code)
        if not it: unknown.append(code); continue
        before = json.dumps(it, sort_keys=True)
        if ip is not None and g(ip) is not None: it['price'] = num(g(ip))
        if io_ is not None and g(io_) is not None: it['old_price'] = num(g(io_))
        if iq is not None and g(iq) is not None:
            q = g(iq)
            it['stock'] = num(q) if re.match(r'^\d[\d\s.,]*$', q) else None
        if ix is not None and g(ix) is not None: it['sold'] = yes(g(ix))
        b = set(it.get('badges') or [])
        for k, i in ib.items():
            if i is not None and g(i) is not None: (b.add if yes(g(i)) else b.discard)(k)
        it['badges'] = [k for k, _ in BADGES if k in b]
        if ih is not None and g(ih) is not None: it['hidden'] = yes(g(ih))
        if json.dumps(it, sort_keys=True) != before: changed.append(it['name'])
    return changed, unknown


# ------------------------------------------------------------------ auth
FAILS = {}

def csrf():
    if '_csrf' not in session: session['_csrf'] = secrets.token_urlsafe(24)
    return session['_csrf']

def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get('ok'): return redirect(url_for('login', next=request.path))
        if request.method == 'POST' and not hmac.compare_digest(request.form.get('_csrf', ''), session.get('_csrf', '')): abort(400)
        return f(*a, **k)
    return w

@app.route('/login', methods=['GET', 'POST'])
def login():
    err = None
    if request.method == 'POST':
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0]
        n, t = FAILS.get(ip, (0, 0))
        pw = os.environ.get('ADMIN_PASSWORD', '')
        if n >= 5 and time.time() - t < 600:
            err = 'Too many wrong tries. Wait 10 minutes.'
        elif pw and hmac.compare_digest(request.form.get('password', ''), pw):
            FAILS.pop(ip, None); session.clear(); session.permanent = True; session['ok'] = True
            nxt = request.args.get('next', '/')
            return redirect(nxt if nxt.startswith('/') and not nxt.startswith('//') else '/')
        else:
            FAILS[ip] = (n + 1, time.time()); err = 'Wrong password.' if pw else 'ADMIN_PASSWORD is not set on the server.'
    return render_template_string(BASE, title='Login', body=LOGIN, err=err)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))


# ------------------------------------------------------------------ pages
def status(it):
    st = it.get('stock')
    if it.get('sold') or st == 0: return 'sold', 'Sold out'
    if st is None: return 'ask', 'Ask'
    return ('few', 'Last pieces') if st <= 5 else ('instock', 'In stock')

@app.route('/')
@login_required
def index():
    items = load()
    q = request.args.get('q', '').lower().strip()
    flt = request.args.get('f', '')
    live = [it for it in items if not it.get('hidden') and it.get('photos')]
    groups = {'all': items, 'site': live, 'hidden': [it for it in items if it not in live]}
    for k in ('instock', 'few', 'ask', 'sold'): groups[k] = [it for it in live if status(it)[0] == k]
    for k in ('new', 'sale', 'hot'): groups[k] = [it for it in live if k in (it.get('badges') or [])]
    pieces = sum(it.get('stock') or 0 for it in live if status(it)[0] != 'sold')
    rows = [it for it in groups.get(flt, items) if not q or q in it['name'].lower() or q in it['slug']]
    rows.sort(key=lambda it: (bool(it.get('hidden')), it['name'].lower()))
    tiles = [('site', 'On the website', ''), ('instock', 'In stock', 't-instock'), ('few', 'Last pieces (1-5)', 't-few'),
             ('ask', 'Stock unknown', ''), ('sold', 'Out of stock', 't-sold'), ('new', 'New arrival', 't-new'),
             ('sale', 'On sale', 't-sale'), ('hot', 'Hot item', 't-hot'), ('hidden', 'Hidden / no photos', '')]
    return render_template_string(BASE, title='Chairs', body=INDEX, rows=rows, q=q, f=flt, status=status, total=len(items),
                                  tiles=[(k, l, c, len(groups[k])) for k, l, c in tiles], pieces=pieces, sheet=bool(SHEET_CSV))

@app.route('/img/<slug>/<name>')
@login_required
def img(slug, name):
    if not re.fullmatch(r'[\w.-]+', slug) or not re.fullmatch(r'[\w.-]+\.jpg', name): abort(404)
    data = STORE.read(f'{IMG}/{slug}/{name}')
    if data is None: abort(404)
    return Response(data, mimetype='image/jpeg', headers={'Cache-Control': 'private, max-age=300'})

def thumb(it, p):
    sm = p[:-4] + '-sm.jpg'
    return url_for('img', slug=it['slug'], name=sm if sm in (it.get('_sm') or []) else p)

@app.route('/chair/<slug>', methods=['GET', 'POST'])
@login_required
def chair(slug):
    with LOCK:
        items = load(); it = find(items, slug)
        if request.method == 'POST':
            f = request.form
            it['name'] = f.get('name', it['name']).strip() or it['name']
            it['price'] = num(f.get('price'))
            it['old_price'] = num(f.get('old_price'))
            s = f.get('stock', '').strip()
            it['stock'] = num(s) if s else None
            it['sold'] = 'sold' in f
            it['hidden'] = 'hidden' in f
            it['badges'] = [k for k, _ in BADGES if k in f.getlist('badges')]
            save(items, f'Update {it["name"]}')
            flash(f'Saved {it["name"]}. The website updates in about 2 minutes.')
            return redirect(url_for('chair', slug=slug))
    files = []
    for p in it.get('photos') or []:
        sm = p[:-4] + '-sm.jpg'
        files.append((p, url_for('img', slug=slug, name=p), url_for('img', slug=slug, name=sm if STORE.read(f'{IMG}/{slug}/{sm}') else p)))
    return render_template_string(BASE, title=it['name'], body=CHAIR, it=it, badges=BADGES, files=files, status=status, site=SITE)

@app.route('/chair/<slug>/photos', methods=['POST'])
@login_required
def photos(slug):
    with LOCK:
        items = load(); it = find(items, slug)
        ph = list(it.get('photos') or [])
        act, name = request.form.get('act'), request.form.get('photo', '')
        extra, msg = {}, None
        if act == 'upload':
            ups = [u for u in request.files.getlist('files') if u and u.filename]
            if not ups: flash('Choose at least one photo first.'); return redirect(url_for('chair', slug=slug))
            stamp = time.strftime('%Y%m%d%H%M%S')
            for k, u in enumerate(ups):
                try: big, small = make_photo(u.read(), request.form.get('mode', 'crop'))
                except Exception: flash(f'Could not read {u.filename}: is it a photo?'); continue
                fn = f'p{stamp}{k:02d}.jpg'
                extra[f'{IMG}/{slug}/{fn}'] = big; extra[f'{IMG}/{slug}/{fn[:-4]}-sm.jpg'] = small
                ph.insert(0, fn) if request.form.get('where') == 'first' else ph.append(fn)
            msg = f'Add {len(extra) // 2} photo(s) to {it["name"]}'
        elif name in ph:
            i = ph.index(name)
            if act == 'delete':
                ph.remove(name); extra[f'{IMG}/{slug}/{name}'] = None
                if STORE.read(f'{IMG}/{slug}/{name[:-4]}-sm.jpg') is not None: extra[f'{IMG}/{slug}/{name[:-4]}-sm.jpg'] = None
                msg = f'Remove a photo from {it["name"]}'
            elif act == 'first': ph.insert(0, ph.pop(i)); msg = f'New cover photo for {it["name"]}'
            elif act == 'left' and i > 0: ph[i - 1], ph[i] = ph[i], ph[i - 1]; msg = f'Reorder photos of {it["name"]}'
            elif act == 'right' and i < len(ph) - 1: ph[i + 1], ph[i] = ph[i], ph[i + 1]; msg = f'Reorder photos of {it["name"]}'
        if msg:
            it['photos'] = ph; save(items, msg, extra)
            flash('Photos saved. The website updates in about 2 minutes.')
    return redirect(url_for('chair', slug=slug) + '#photos')

@app.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        with LOCK:
            items = load()
            name = request.form.get('name', '').strip()
            if not name: flash('Type the chair code first.'); return redirect(url_for('new'))
            slug = base = slugify(name); n = 2
            while any(i['slug'] == slug for i in items): slug = f'{base}-{n}'; n += 1
            s = request.form.get('stock', '').strip()
            items.append({'folder': name, 'name': name, 'slug': slug, 'price': num(request.form.get('price')), 'stock': num(s) if s else None,
                          'sold': False, 'sheet': name, 'hidden': False, 'photos': [], 'badges': ['new'], 'old_price': None})
            save(items, f'Add new chair {name}')
        flash(f'{name} added. Now add its photos: a chair shows on the website once it has at least one photo.')
        return redirect(url_for('chair', slug=slug) + '#photos')
    return render_template_string(BASE, title='Add a chair', body=NEW)

@app.route('/export.csv')
@login_required
def export():
    return Response(to_csv(load()), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=magnetix-chairs-{time.strftime("%Y-%m-%d")}.csv'})

@app.route('/import', methods=['POST'])
@login_required
def import_csv():
    src = request.form.get('src')
    try:
        if src == 'sheet':
            if not SHEET_CSV: raise ValueError('No Google Sheet link is set.')
            r = requests.get(SHEET_CSV, timeout=30); r.raise_for_status(); r.encoding = 'utf-8'; text = r.text
        else:
            f = request.files.get('file')
            if not f or not f.filename: raise ValueError('Choose a CSV file first.')
            text = f.read().decode('utf-8-sig', errors='replace')
        with LOCK:
            items = load(); changed, unknown = apply_csv(items, text)
            if changed: save(items, f'Update {len(changed)} chairs from {"Google Sheet" if src == "sheet" else "CSV upload"}')
        flash(f'Updated {len(changed)} chair(s)' + (f': {", ".join(changed[:12])}{"…" if len(changed) > 12 else ""}' if changed else '. Nothing was different.')
              + (f' Codes not found (skipped): {", ".join(unknown[:10])}.' if unknown else '') + (' The website updates in about 2 minutes.' if changed else ''))
    except ValueError as ex:
        flash(str(ex))
    except requests.RequestException:
        flash('Could not read the Google Sheet. Is it still published to the web?')
    return redirect(url_for('index'))

@app.errorhandler(413)
def too_big(_):
    flash('Those files are too big together (max 60 MB per upload). Try fewer photos at a time.')
    return redirect(request.referrer or '/')

@app.context_processor
def ctx(): return {'csrf': csrf}


# ------------------------------------------------------------------ templates
BASE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>{{ title }} · Magnetix admin</title>
<style>
:root{--gold:#d4ae6a;--ink:#141414;--line:#e6dfd1;--bg:#f6f2ea}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
a{color:inherit}header{background:#0e0e0e;color:#fff;padding:12px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header b{color:var(--gold);letter-spacing:.04em}header nav{display:flex;gap:14px;flex-wrap:wrap;margin-left:auto}header a{text-decoration:none;opacity:.85}
main{max-width:1100px;margin:0 auto;padding:18px 16px 60px}h1{font-size:22px;margin:6px 0 14px}
.flash{background:#fff7e3;border:1px solid #ecd9a6;padding:10px 14px;border-radius:10px;margin-bottom:14px}
.btn{display:inline-block;border:0;border-radius:10px;padding:9px 14px;font:inherit;font-weight:600;cursor:pointer;background:var(--gold);color:#111;text-decoration:none}
.btn.line{background:#fff;border:1px solid var(--line)}.btn.red{background:#b3261e;color:#fff}.btn.sm{padding:5px 9px;font-size:13px}
.box{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:16px}
input[type=text],input[type=number],input[type=password],input[type=search]{font:inherit;padding:9px 11px;border:1px solid #d8d0bf;border-radius:9px;width:100%;background:#fff}
label{display:block;font-weight:600;margin:10px 0 4px}.chk{display:flex;gap:8px;align-items:center;font-weight:500;margin:6px 0}
.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.list{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}
.it{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;text-decoration:none;display:block}
.it img{width:100%;aspect-ratio:4/5;object-fit:cover;display:block;background:#fafafa}.it div{padding:8px 10px}.it.hid{opacity:.45}
.it small{color:#666}.tag{display:inline-block;font-size:11px;font-weight:700;padding:2px 7px;border-radius:99px;margin:2px 2px 0 0;background:#eee}
.t-new{background:#1f6f4a;color:#fff}.t-sale{background:#c0392b;color:#fff}.t-hot{background:#e8892b;color:#fff}.t-sold{background:#2a2a2a;color:#fff}.t-few{background:#fff1d6;color:#8a5a00}.t-instock{background:#e5f4e8;color:#1c6b33}
.ph{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}.ph figure{margin:0;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.ph img{width:100%;aspect-ratio:4/5;object-fit:cover;display:block}.ph figcaption{display:flex;gap:4px;flex-wrap:wrap;padding:6px}.ph form{display:inline}
.stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:16px}
.stat{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 12px;text-decoration:none;display:flex;flex-direction:column;gap:4px}
.stat b{font-size:26px;line-height:1}.stat.on{outline:3px solid var(--gold)}
.cover{outline:3px solid var(--gold)}.muted{color:#666;font-size:13px}.tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
</style></head><body>
{% if session.ok %}<header><b>MAGNETIX · admin</b><nav><a href="/">All chairs</a><a href="/new">+ Add chair</a><a href="{{ site if site is defined else 'https://magnetix.onrender.com' }}" target="_blank">Open website ↗</a><a href="/logout">Log out</a></nav></header>{% endif %}
<main>{% with m = get_flashed_messages() %}{% for x in m %}<div class="flash">{{ x }}</div>{% endfor %}{% endwith %}
{% if err %}<div class="flash">{{ err }}</div>{% endif %}
{{ content }}</main></body></html>'''

LOGIN = r'''<div class="box" style="max-width:360px;margin:60px auto"><h1>Magnetix admin</h1>
<form method="post"><label>Password</label><input type="password" name="password" autofocus required><p><button class="btn">Log in</button></p></form></div>'''

INDEX = r'''<h1>Chairs <span class="muted">({{ total }} models)</span></h1>
<div class="stats">{% for k, l, c, n in tiles %}<a href="/?f={{ k }}" class="stat{{ ' on' if f == k }}"><b>{{ n }}</b><span class="tag {{ c }}">{{ l }}</span></a>{% endfor %}
<div class="stat"><b>{{ '{:,}'.format(pieces).replace(',', ' ') }}</b><span class="tag">Pieces in stock (website chairs)</span></div></div>
{% for k, l, c, n in tiles if k == f %}<p>Showing only: <b>{{ l }}</b> ({{ n }}) · <a href="/">show all</a></p>{% endfor %}
<div class="box"><div class="tools">
<a class="btn" href="/export.csv">⬇ Download all as CSV</a>
<form method="post" action="/import" enctype="multipart/form-data" class="tools" style="margin:0"><input type="hidden" name="_csrf" value="{{ csrf() }}">
<input type="file" name="file" accept=".csv,text/csv" required><button class="btn line" name="src" value="file">⬆ Upload CSV</button></form>
{% if sheet %}<form method="post" action="/import" style="margin:0"><input type="hidden" name="_csrf" value="{{ csrf() }}"><button class="btn line" name="src" value="sheet">⟳ Import from Google Sheet</button></form>{% endif %}
</div><p class="muted">Download the CSV, change prices, stock or badges in Excel or Google Sheets (keep the Code column as it is), then upload it. Only the columns in the file are changed.</p></div>
<form class="tools"><input type="search" name="q" value="{{ q }}" placeholder="Search by code…" style="max-width:260px"><button class="btn line">Search</button></form>
<div class="list">{% for it in rows %}{% set st = status(it) %}
<a class="it{{ ' hid' if it.hidden }}" href="/chair/{{ it.slug }}">
{% if it.photos %}<img loading="lazy" src="/img/{{ it.slug }}/{{ it.photos[0][:-4] }}-sm.jpg" onerror="this.onerror=null;this.src='/img/{{ it.slug }}/{{ it.photos[0] }}'" alt="">{% else %}<img alt="">{% endif %}
<div><b>{{ it.name }}</b><br><small>{{ '{:,}'.format(it.price).replace(',', ' ') ~ ' AMD' if it.price else 'no price' }} · stock {{ it.stock if it.stock is not none else '?' }}</small><br>
<span class="tag t-{{ st[0] }}">{{ st[1] }}</span>{% for b in it.badges or [] %}<span class="tag t-{{ b }}">{{ {'new':'New','sale':'Sale','hot':'Hot'}[b] }}</span>{% endfor %}{% if it.hidden %}<span class="tag">Hidden</span>{% endif %}{% if not it.photos %}<span class="tag">No photos</span>{% endif %}</div></a>
{% endfor %}</div>'''

CHAIR = r'''<p><a href="/">← All chairs</a></p><h1>{{ it.name }} {% if not it.hidden and it.photos %}<a class="muted" href="{{ site }}/chair/{{ it.slug }}/" target="_blank">view on website ↗</a>{% endif %}</h1>
<form method="post" class="box"><input type="hidden" name="_csrf" value="{{ csrf() }}">
<div class="row"><div><label>Code / name</label><input type="text" name="name" value="{{ it.name }}"></div>
<div><label>Price (AMD)</label><input type="number" name="price" min="0" step="500" value="{{ it.price or '' }}"></div>
<div><label>Stock (pieces)</label><input type="number" name="stock" min="0" value="{{ it.stock if it.stock is not none else '' }}" placeholder="empty = ask"></div>
<div><label>Old price (for On sale)</label><input type="number" name="old_price" min="0" step="500" value="{{ it.old_price or '' }}"></div></div>
<label>Badges</label>{% for k, l in badges %}<label class="chk"><input type="checkbox" name="badges" value="{{ k }}"{{ ' checked' if k in (it.badges or []) }}> {{ l }}</label>{% endfor %}
<label class="chk"><input type="checkbox" name="sold"{{ ' checked' if it.sold }}> Out of stock / sold out <span class="muted">(also automatic when stock is 0)</span></label>
<label class="chk"><input type="checkbox" name="hidden"{{ ' checked' if it.hidden }}> Hide from the website</label>
<p class="muted">Now: <span class="tag t-{{ status(it)[0] }}">{{ status(it)[1] }}</span>. Stock 1-5 shows "Last pieces". Empty stock shows "Ask about stock". On sale shows the old price crossed out.</p>
<button class="btn">Save changes</button></form>
<div class="box" id="photos"><h2 style="margin-top:0;font-size:18px">Photos <span class="muted">(first photo = cover in the catalog; the 4th shows when you hover over a card)</span></h2>
<div class="ph">{% for p, big, small in files %}<figure class="{{ 'cover' if loop.first }}"><a href="{{ big }}" target="_blank"><img loading="lazy" src="{{ small }}" alt=""></a><figcaption>
{% for act, lab in [('first','★ Cover'),('left','←'),('right','→')] %}<form method="post" action="/chair/{{ it.slug }}/photos"><input type="hidden" name="_csrf" value="{{ csrf() }}"><input type="hidden" name="photo" value="{{ p }}"><button class="btn line sm" name="act" value="{{ act }}">{{ lab }}</button></form>{% endfor %}
<form method="post" action="/chair/{{ it.slug }}/photos" onsubmit="return confirm('Remove this photo from the website?')"><input type="hidden" name="_csrf" value="{{ csrf() }}"><input type="hidden" name="photo" value="{{ p }}"><button class="btn red sm" name="act" value="delete">✕</button></form>
</figcaption></figure>{% else %}<p class="muted">No photos yet.</p>{% endfor %}</div>
<form method="post" action="/chair/{{ it.slug }}/photos" enctype="multipart/form-data" style="margin-top:14px"><input type="hidden" name="_csrf" value="{{ csrf() }}">
<label>Add photos</label><input type="file" name="files" accept="image/*" multiple required>
<label class="chk"><input type="radio" name="mode" value="crop" checked> Fill the frame (cuts the edges a little)</label>
<label class="chk"><input type="radio" name="mode" value="fit"> Show the whole photo on white</label>
<label class="chk"><input type="checkbox" name="where" value="first"> Make the first new photo the cover</label>
<p><button class="btn" name="act" value="upload">Upload</button> <span class="muted">Photos are resized to 960×1200 automatically.</span></p></form></div>'''

NEW = r'''<p><a href="/">← All chairs</a></p><h1>Add a chair</h1>
<form method="post" class="box" style="max-width:520px"><input type="hidden" name="_csrf" value="{{ csrf() }}">
<label>Code / name</label><input type="text" name="name" placeholder="e.g. 6615A Black" required>
<div class="row"><div><label>Price (AMD)</label><input type="number" name="price" min="0" step="500"></div><div><label>Stock</label><input type="number" name="stock" min="0"></div></div>
<p class="muted">It gets the "New arrival" badge. Add photos on the next page.</p><button class="btn">Add chair</button></form>'''

_rts = render_template_string
def render_template_string(src, body='', **kw):  # noqa: F811  page body first, then the shared frame around it
    from markupsafe import Markup
    return _rts(src, content=Markup(_rts(body, **kw)), **kw)

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', 5000)), debug=bool(os.environ.get('LOCAL_REPO')))
