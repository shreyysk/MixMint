"""Render one MixMint promo video (runs on GitHub Actions, see .github/workflows/promo-render.yml).

    JOB_URL   signed link to /promo/job/<id>/  -> clip download link, upload links and the text
    DONE_URL  signed link to /promo/job/<id>/done/  <- result

Templates (1080x1920, H.264/AAC, max 59 s, last 2.5 s is an end card):
    mint   video fills the screen, dark fade at the bottom with title, DJ and price
    bold   ink background, square video in the middle, big title above/below
    clean  video fills the screen, small logo only

Text stays out of the areas Instagram/YouTube cover with their buttons (right 140 px, bottom 360 px).
Local test:  python tools/promo/render.py --local in.mp4 out.mp4 [mint|bold|clean]
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
MINT = (0, 255, 179)
INK = (10, 10, 15)
CREAM = (245, 240, 232)
ROOT = Path(__file__).resolve().parents[2]
LOGO = ROOT / "static" / "logo" / "MIXMINT_WHITE.png"
FONT_DIR = Path(tempfile.gettempdir()) / "mm-fonts"
FONTS = {
    "bold": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf",
    "medium": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Medium.ttf",
}
END = 2.5


# ─────────────────────────────── helpers ───────────────────────────────
def font(kind, size):
    FONT_DIR.mkdir(exist_ok=True)
    path = FONT_DIR / f"{kind}.ttf"
    if not path.exists():
        try:
            urllib.request.urlretrieve(FONTS[kind], path)
        except Exception:
            pass
    for p in (path, Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap(draw, text, fnt, width, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=fnt) <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and draw.textlength(lines[-1] + "…", font=fnt) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines


def fit_font(draw, text, kind, start, minimum, width, max_lines):
    size = start
    while size > minimum:
        f = font(kind, size)
        if len(wrap(draw, text, f, width, 99)) <= max_lines:
            return f
        size -= 4
    return font(kind, minimum)


def logo(width):
    try:
        im = Image.open(LOGO).convert("RGBA")
        bbox = im.getbbox()
        if bbox:
            im = im.crop(bbox)
        return im.resize((width, max(1, int(im.height * width / im.width))), Image.LANCZOS)
    except Exception:
        im = Image.new("RGBA", (width, 80), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), "MIXMINT", font=font("bold", 64), fill=(255, 255, 255, 255))
        return im


def pill(draw, xy, text, fnt, fill, color, pad=(28, 14)):
    x, y = xy
    tw = draw.textlength(text, font=fnt)
    asc, desc = fnt.getmetrics()
    h = asc + desc + pad[1] * 2
    draw.rounded_rectangle((x, y, x + tw + pad[0] * 2, y + h), radius=h // 2, fill=fill)
    draw.text((x + pad[0], y + pad[1]), text, font=fnt, fill=color)
    return h


def text_block(draw, x, y, job, width, title_start=92):
    """Kind pill, title, DJ name, price/site pill. Returns the bottom y."""
    y += pill(draw, (x, y), job["kind"].upper(), font("bold", 30), MINT, INK) + 26
    tf = fit_font(draw, job["title"], "bold", title_start, 56, width, 2)
    for line in wrap(draw, job["title"], tf, width, 2):
        draw.text((x, y), line, font=tf, fill=(255, 255, 255, 255))
        y += int(tf.size * 1.12)
    df = font("medium", 46)
    by = wrap(draw, f"by {job['dj']}", df, width, 1)[0]
    draw.text((x, y + 6), by, font=df, fill=MINT + (255,))
    y += 76
    y += pill(draw, (x, y + 10), f"{job['price']}  ·  {job['site']}", font("bold", 36), (255, 255, 255, 235), INK) + 10
    return y


# ─────────────────────────────── overlays ───────────────────────────────
def overlay(job, template):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if template == "clean":
        lg = logo(140)
        lg.putalpha(lg.getchannel("A").point(lambda a: int(a * 0.85)))
        im.alpha_composite(lg, (60, 90))
        f = font("bold", 34)
        pill(d, (60, H - 470), f"{job['title'][:34]} · {job['site']}", f, (10, 10, 15, 170), (255, 255, 255, 255), pad=(24, 12))
        return im
    if template == "bold":
        lg = logo(150)
        im.alpha_composite(lg, (60, 70))
        d.text((60 + lg.width + 30, 70 + lg.height // 2 - 22), "NEW ON MIXMINT", font=font("bold", 38), fill=MINT + (255,))
        text_block(d, 60, 1330, job, W - 200, title_start=80)
        return im
    # mint: top shade + bottom fade
    shade = Image.new("L", (1, H), 0)
    for yy in range(H):
        a = 0
        if yy < 320:
            a = int(150 * (1 - yy / 320))
        elif yy > 940:
            a = int(min(1, (yy - 940) / 520) * 235)
        shade.putpixel((0, yy), a)
    dark = Image.new("RGBA", (W, H), INK + (0,))
    dark.putalpha(shade.resize((W, H)))
    im.alpha_composite(dark)
    im.alpha_composite(logo(160), (60, 80))
    text_block(d, 60, 1150, job, W - 200)
    return im


def end_card(job, cover_path):
    im = Image.new("RGBA", (W, H), INK + (255,))
    d = ImageDraw.Draw(im)
    if cover_path:
        try:
            c = Image.open(cover_path).convert("RGB")
            side = min(c.size)
            c = c.crop(((c.width - side) // 2, (c.height - side) // 2, (c.width + side) // 2, (c.height + side) // 2))
            bg = c.resize((W, W)).filter(ImageFilter.GaussianBlur(60)).resize((W, H))
            bg = Image.blend(bg, Image.new("RGB", (W, H), INK), 0.72)
            im.paste(bg)
            im.paste(c.resize((720, 720), Image.LANCZOS), (180, 330))
        except Exception:
            pass
    im.alpha_composite(logo(180), ((W - 180) // 2, 110))
    tf = fit_font(d, job["title"], "bold", 76, 50, W - 160, 2)
    y = 1100
    for line in wrap(d, job["title"], tf, W - 160, 2):
        d.text(((W - d.textlength(line, font=tf)) / 2, y), line, font=tf, fill=(255, 255, 255, 255))
        y += int(tf.size * 1.12)
    df = font("medium", 44)
    t = f"by {job['dj']}"
    d.text(((W - d.textlength(t, font=df)) / 2, y + 8), t, font=df, fill=MINT + (255,))
    cta = f"Get it on {job['site']}  ·  {job['price']}"
    cf = font("bold", 40)
    tw = d.textlength(cta, font=cf)
    pill(d, (int((W - tw) / 2) - 32, y + 110), cta, cf, MINT, INK, pad=(32, 18))
    return im


# ─────────────────────────────── ffmpeg ───────────────────────────────
def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:stream_side_data=rotation:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v:
        raise ValueError("That file has no video.")
    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    rot = 0
    for sd in v.get("side_data_list") or []:
        rot = abs(int(float(sd.get("rotation", 0) or 0)))
    if rot in (90, 270):
        w, h = h, w
    audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    return w, h, float(data.get("format", {}).get("duration") or 0), audio


def render(src, dst, job, template, cover=None, workdir=None):
    workdir = Path(workdir or tempfile.mkdtemp())
    w, h, dur, audio = probe(src)
    if dur < 3:
        raise ValueError("The video is shorter than 3 seconds.")
    D = round(min(dur, float(job.get("max_seconds", 59))), 2)
    ov, ec = workdir / "overlay.png", workdir / "end.png"
    overlay(job, template).save(ov)
    end_card(job, cover).save(ec)
    fill = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    if template == "bold":
        video = (f"color=c=0x0A0A0F:s=1080x1920:d={D}[base];"
                 "[0:v]scale=1000:1000:force_original_aspect_ratio=increase,crop=1000:1000,setsar=1[sq];"
                 "[base][sq]overlay=40:340:shortest=1[v0]")
    elif w > h * 1.05:  # landscape: blurred fill behind, whole frame in the middle
        video = (f"[0:v]split[a][b];[a]{fill},boxblur=24:2,eq=brightness=-0.12[bg];"
                 "[b]scale=1080:-2,setsar=1[fg];[bg][fg]overlay=0:(H-h)/2-80[v0]")
    else:
        video = f"[0:v]{fill}[v0]"
    graph = (f"{video};[v0][1:v]overlay=0:0[v1];"
             f"[2:v]format=rgba,fade=t=in:st={D - END}:d=0.4:alpha=1[e];"
             f"[v1][e]overlay=0:0:enable='gte(t,{D - END})',fps=30,format=yuv420p,fade=t=in:st=0:d=0.3[v]")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-t", str(D), "-i", str(src),
           "-loop", "1", "-t", str(D), "-i", str(ov), "-loop", "1", "-t", str(D), "-i", str(ec),
           "-filter_complex", graph, "-map", "[v]"]
    if audio:
        cmd += ["-map", "0:a:0", "-af", f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={max(0, D - 1.5)}:d=1.5",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += ["-t", str(D), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-profile:v", "high",
            "-level", "4.1", "-maxrate", "5M", "-bufsize", "10M", "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True)
    thumb = Path(dst).with_suffix(".jpg")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", str(min(1.5, D / 3)), "-i", str(dst),
                    "-frames:v", "1", "-q:v", "3", str(thumb)], check=True)
    return D, thumb


# ─────────────────────────────── job runner ───────────────────────────────
def _get(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "MixMint-promo-render"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def _put(url, path, ctype):
    data = Path(path).read_bytes()
    req = urllib.request.Request(url, data=data, method="PUT", headers={"Content-Type": ctype, "Content-Length": str(len(data))})
    with urllib.request.urlopen(req, timeout=300) as r:
        if r.status >= 300:
            raise RuntimeError(f"upload failed ({r.status})")


def _post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "MixMint-promo-render"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status


def run_job(job_url, done_url):
    try:
        with urllib.request.urlopen(urllib.request.Request(job_url, headers={"User-Agent": "MixMint-promo-render"}), timeout=60) as r:
            job = json.loads(r.read())
        work = Path(tempfile.mkdtemp())
        src, out = work / "in.bin", work / "out.mp4"
        _get(job["raw_url"], src)
        cover = None
        if job.get("cover_url"):
            try:
                cover = work / "cover.img"
                _get(job["cover_url"], cover)
            except Exception:
                cover = None
        dur, thumb = render(src, out, job, job.get("template", "mint"), cover, work)
        _put(job["output"]["url"], out, "video/mp4")
        _put(job["thumb"]["url"], thumb, "image/jpeg")
        _post(done_url, {"ok": True, "output_key": job["output"]["key"], "thumb_key": job["thumb"]["key"], "duration": dur})
        print(f"Rendered promo {job['id']}: {dur:.1f}s")
    except Exception as exc:
        msg = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            msg = "ffmpeg couldn't read or encode that video."
        print(f"Render failed: {type(exc).__name__}", file=sys.stderr)
        try:
            _post(done_url, {"ok": False, "error": msg[:400]})
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--local":
        sample = {"title": "Kantara Varaha Roopam (DJ Remix)", "dj": "DJ Shreyy", "price": "₹99", "kind": "New drop",
                  "site": "mixmint.site", "max_seconds": 59}
        print(render(sys.argv[2], sys.argv[3], sample, sys.argv[4] if len(sys.argv) > 4 else "mint"))
    else:
        run_job(os.environ["JOB_URL"], os.environ["DONE_URL"])
