"""Frame every white-background photo the same way: chair 80% of canvas height, centred, floor at 94%."""
import os, sys
from PIL import Image, ImageChops, ImageOps
import numpy as np
W, H = 960, 1200
def norm(p):
    im = Image.open(p).convert('RGB'); a = np.asarray(im).astype(int)
    corners = np.concatenate([a[:20,:20].reshape(-1,3), a[:20,-20:].reshape(-1,3), a[-20:,:20].reshape(-1,3), a[-20:,-20:].reshape(-1,3)])
    bg = tuple(int(v) for v in np.median(corners, 0))
    diff = np.abs(a - np.array(bg)).max(2) > 28
    ys, xs = np.where(diff)
    if len(xs) < 500: return None
    x0, x1 = np.percentile(xs, [0.2, 99.8]).astype(int); y0, y1 = np.percentile(ys, [0.1, 99.9]).astype(int)
    pad = 6; x0, y0 = max(0, x0-pad), max(0, y0-pad); x1, y1 = min(im.width, x1+pad), min(im.height, y1+pad)
    crop = im.crop((x0, y0, x1, y1))
    s = min(0.80*H/crop.height, 0.86*W/crop.width)
    crop = crop.resize((round(crop.width*s), round(crop.height*s)), Image.LANCZOS)
    cv = Image.new('RGB', (W, H), (255, 255, 255))
    # soften the old background into white: lift near-bg pixels
    ca = np.asarray(crop).astype(int); d = np.abs(ca - np.array(bg)).max(2)
    alpha = np.clip((d - 6) / 22, 0, 1)[..., None]
    ca = (ca * alpha + 255 * (1 - alpha)).astype('uint8')
    crop = Image.fromarray(ca)
    bottom = round(H*0.94); top = bottom - crop.height
    cv.paste(crop, ((W - crop.width)//2, top))
    return cv
root = 'public/img'
for s in sorted(os.listdir(root)):
    for n in ['semi', 'front', 'side']:
        p = f'{root}/{s}/{n}.jpg'
        if not os.path.exists(p): continue
        out = norm(p)
        if out is None: print('skip', p); continue
        out.save(p, quality=82, optimize=True, progressive=True)
        if n == 'semi':
            t = out.copy(); t.thumbnail((480, 600), Image.LANCZOS); t.save(f'{root}/{s}/semi-sm.jpg', quality=80, optimize=True, progressive=True)
print('done')
