#!/usr/bin/env python3
"""
lm_ingest.py — image standardizer with four output modes.

  A) STANDARDIZE      (--out <folder>)
       python3 lm_ingest.py --src "~/in" --out "~/clean"

  B) SLIDESHOW TOUR   (--tour <file.html>)   ── low-tech, no map, no coords ──
       python3 lm_ingest.py --src "~/in" --tour "~/draft/tour.html"

  C) MAP TOUR         (--map-tour <file.html>)   ── geographic Leaflet tour ──
       Standardise + generate a self-contained map tour with images wired in.
       Coordinates are SEEDED from a default list (Chang'an / Heian-kyo /
       Forbidden City) and recycled if there are more images than seed points,
       so the map renders immediately; you then set real lat/lng per stop.
       python3 lm_ingest.py --src "~/in" --map-tour "~/draft/maptour.html"

  D) LEARN MORE ENTRY (--site + --project)   ── writes learn-more.NEW.json ──
       python3 lm_ingest.py --src "~/in" --site chiang-mai --project "~/repo/portabletemple"

  Modes B, C and D never touch your repo's master learn-more.json.

OPTIONS
  --src       Folder of source images.                     [required]
  --out       Mode A: write cleaned images here.
  --tour      Mode B: write a slideshow html here.
  --map-tour  Mode C: write a Leaflet map tour html here.
  --site      Mode D: site id.
  --project   Mode D: path to portabletemple/.
  --max       Max long-edge px (downscale only).           [default 1600]
  --quality   JPEG quality 1-95.                           [default 85]
  --dry-run   Show what would happen; write nothing.

DEPENDENCY:  pip3 install Pillow      (and pip3 install pillow-heif for .heic)
"""

import argparse, json, os, re, sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow is not installed. Run:  pip3 install Pillow")

try:
    import pillow_heif  # type: ignore
    pillow_heif.register_heif_opener()
    HEIC_OK = True
except Exception:
    HEIC_OK = False

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp", ".gif", ".heic", ".heif"}

# Seed coordinates for --map-tour (the three square cities). Recycled if more images.
DEFAULT_COORDS = [
    {"lat": 34.2220, "lng": 108.9530, "zoom": 11},   # Chang'an / Xi'an
    {"lat": 35.0116, "lng": 135.7440, "zoom": 12},   # Heian-kyo / Kyoto
    {"lat": 39.9163, "lng": 116.3972, "zoom": 13},   # Forbidden City / Beijing
]


def slugify(stem: str) -> str:
    s = stem.strip().lower().replace("_", "-").replace(" ", "-")
    s = re.sub(r"[^a-z0-9.\-]", "", s)
    return re.sub(r"-{2,}", "-", s).strip("-") or "image"


def label_from_stem(stem: str) -> str:
    s = re.sub(r"^[\s0-9._\-]+", "", stem.strip()).replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s.title() if s else stem


def gather(src: Path):
    sources = sorted([p for p in src.iterdir()
                      if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
                     key=lambda p: p.name.lower())
    heic = [p for p in sources if p.suffix.lower() in (".heic", ".heif")]
    if heic and not HEIC_OK:
        print(f"  ! {len(heic)} .heic file(s) will be SKIPPED - install pillow-heif to include them.")
        sources = [p for p in sources if p.suffix.lower() not in (".heic", ".heif")]
    return sources


def process_image(src_path: Path, out_noext: Path, max_edge: int, quality: int) -> Path:
    with Image.open(src_path) as im:
        im = ImageOps.exif_transpose(im)
        if src_path.suffix.lower() == ".png":
            out = out_noext.with_suffix(".png")
            if im.mode not in ("RGBA", "RGB", "P", "LA", "L"):
                im = im.convert("RGBA")
            im.thumbnail((max_edge, max_edge), Image.LANCZOS)
            im.save(out, format="PNG", optimize=True)
        else:
            out = out_noext.with_suffix(".jpg")
            if im.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", im.size, (255, 255, 255))
                im = im.convert("RGBA"); bg.paste(im, mask=im.split()[-1]); im = bg
            elif im.mode != "RGB":
                im = im.convert("RGB")
            im.thumbnail((max_edge, max_edge), Image.LANCZOS)
            im.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
    return out


_PLACEHOLDER_JS = (
    "'data:image/svg+xml;utf8,'+encodeURIComponent('<svg xmlns=\\\"http://www.w3.org/2000/svg\\\" "
    "width=\\\"400\\\" height=\\\"240\\\"><rect width=\\\"100%\\\" height=\\\"100%\\\" fill=\\\"#1a1814\\\"/>"
    "<text x=\\\"50%\\\" y=\\\"50%\\\" fill=\\\"#8a7f68\\\" font-family=\\\"sans-serif\\\" font-size=\\\"15\\\" "
    "text-anchor=\\\"middle\\\" dominant-baseline=\\\"middle\\\">image goes here</text></svg>')"
)

SLIDESHOW_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Image tour (draft)</title>
<style>
 @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500&display=swap');
 body{margin:0;font-family:'Inter',system-ui,sans-serif;background:#0f0e0a;color:#f5f0e1;height:100vh;display:flex;flex-direction:column}
 header{padding:12px 20px;border-bottom:1px solid #2a261d;color:#8a7f68;font-size:12px}
 header code{color:#c9a44a}
 #stage{flex:1;display:flex;align-items:center;justify-content:center;min-height:0;padding:18px}
 #img{max-width:100%;max-height:100%;object-fit:contain;border-radius:10px;border:1px solid #5c5240;background:#1a1814}
 #bar{padding:14px 20px 24px;border-top:1px solid #2a261d;display:flex;flex-direction:column;gap:6px;align-items:center}
 #title{font-family:'Playfair Display',serif;color:#e8d5a3;font-size:20px;text-align:center}
 #cap{color:#d4c9b0;max-width:680px;text-align:center;line-height:1.6;font-size:15px}
 #ctrls{display:flex;gap:14px;align-items:center;margin-top:6px}
 button{background:#8B6914;color:#fff;border:none;padding:10px 22px;border-radius:999px;font-size:14px;cursor:pointer}
 button:hover{background:#a67c1f}
 #count{font-family:monospace;color:#8a7f68;font-size:13px}
</style>
</head>
<body>
<header>Draft tour &mdash; edit the <code>slides</code> list near the bottom of this file to write captions and reorder. Arrow keys page through.</header>
<div id="stage"><img id="img" alt=""></div>
<div id="bar">
  <div id="title"></div>
  <div id="cap"></div>
  <div id="ctrls">
    <button onclick="go(-1)">&larr; Back</button>
    <span id="count"></span>
    <button onclick="go(1)">Next &rarr;</button>
  </div>
</div>
<script>
/* ===== EDIT BELOW: reorder entries to reorder the tour; replace each "TODO". ===== */
const slides = __SLIDES__;
/* ================================================================================ */
const PH=__PLACEHOLDER__;
let i=0;
function render(){
  const s=slides[i], img=document.getElementById('img');
  img.onerror=function(){img.onerror=null;img.src=PH;};
  img.src=s.image; img.alt=s.label||'';
  document.getElementById('title').textContent=s.label||'';
  document.getElementById('cap').textContent=s.caption||'';
  document.getElementById('count').textContent=(i+1)+' / '+slides.length;
}
function go(d){ i=(i+d+slides.length)%slides.length; render(); }
document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')go(1);if(e.key==='ArrowLeft')go(-1);});
render();
</script>
</body>
</html>
"""

MAP_TOUR_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Map tour (draft)</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
 @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500&display=swap');
 body{margin:0;font-family:'Inter',system-ui,sans-serif;background:#0f0e0a;color:#f5f0e1;overflow:hidden}
 #map{height:100vh;width:100%}
 .leaflet-container{background:#141310}
 #intro{position:fixed;inset:0;z-index:3000;background:#0f0e0a;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;padding:24px;text-align:center;transition:opacity .5s ease}
 #intro.gone{opacity:0;pointer-events:none}
 #intro h1{font-family:'Playfair Display',serif;color:#e8d5a3;font-size:30px;margin:0}
 #intro p{max-width:540px;color:#d4c9b0;line-height:1.6;margin:0}
 #intro code{color:#c9a44a}
 .btn{background:linear-gradient(145deg,#8B6914,#6b4f0f);color:#f5f0e1;border:none;padding:14px 32px;border-radius:999px;font-size:15px;font-weight:600;cursor:pointer;box-shadow:0 8px 25px rgba(139,105,20,.5)}
 .btn:hover{transform:translateY(-2px)}
 #panel{position:fixed;top:24px;bottom:24px;right:24px;width:380px;background:rgba(20,19,16,.96);border:1px solid #5c5240;border-radius:16px;padding:24px;box-shadow:0 20px 60px rgba(0,0,0,.8);z-index:1000;display:none;flex-direction:column;animation:pop .3s cubic-bezier(.34,1.56,.64,1)}
 @keyframes pop{from{opacity:0;transform:translateY(30px) scale(.95)}to{opacity:1;transform:none}}
 #panel-scroll{flex:1 1 auto;min-height:0;overflow-y:auto}
 #panel img{display:block;width:100%;max-height:260px;object-fit:contain;border-radius:10px;margin-bottom:12px;border:1px solid #5c5240;background:#1a1814;cursor:zoom-in}
 #panel h2{margin:4px 0 4px;color:#e8d5a3;font-family:'Playfair Display',serif;font-size:22px}
 #panel .sub{font-size:13px;color:#8a7f68;margin-bottom:12px}
 #panel p{line-height:1.7;color:#d4c9b0;font-size:15px}
 #close{float:right;background:none;border:none;color:#8a7f68;font-size:26px;cursor:pointer;line-height:1}
 #close:hover{color:#e8d5a3}
 #nav{display:flex;justify-content:space-between;align-items:center;flex-shrink:0;margin-top:16px;padding-top:16px;border-top:1px solid #5c5240}
 .tbtn{background:#8B6914;color:#fff;border:none;padding:10px 20px;border-radius:999px;font-size:14px;cursor:pointer}
 .tbtn:hover{background:#a67c1f}
 #prog{font-size:12px;color:#8a7f68;font-family:monospace}
 #lb{position:fixed;inset:0;background:rgba(0,0,0,.88);display:none;align-items:center;justify-content:center;z-index:2000;cursor:zoom-out}
 #lb.on{display:flex} #lb img{max-width:94vw;max-height:84vh;border-radius:10px}
 @media (max-width:700px){#panel{top:auto;bottom:0;left:0;right:0;width:auto;max-height:54vh;border-radius:16px 16px 0 0}#panel img{max-height:150px}}
</style>
</head>
<body>
<div id="intro">
  <h1>Map tour (draft)</h1>
  <p>A draft geographic tour with your images wired in. The pins are placeholder locations &mdash; edit the <code>stops</code> list near the bottom of this file to set real coordinates and captions, and reorder as you like.</p>
  <button class="btn" onclick="begin()">Begin the Tour &rarr;</button>
</div>
<div id="map"></div>
<div id="panel">
  <button id="close" onclick="closePanel()">&times;</button>
  <div id="panel-scroll">
    <img id="p-img" alt="">
    <h2 id="p-title"></h2>
    <div class="sub" id="p-sub"></div>
    <p id="p-text"></p>
  </div>
  <div id="nav">
    <button class="tbtn" id="back" onclick="prev()">&larr; Back</button>
    <div id="prog"></div>
    <button class="tbtn" onclick="next()">Next &rarr;</button>
  </div>
</div>
<div id="lb" onclick="this.classList.remove('on')"><img id="lb-img" alt=""></div>
<script>
/* ===== EDIT BELOW: reorder entries to reorder; set real lat/lng/zoom; replace each "TODO". ===== */
const stops = __STOPS__;
/* ============================================================================================= */
const PLACEHOLDER=__PLACEHOLDER__;
let map,i=0;
function loadImage(el,src){el.onerror=function(){el.onerror=null;el.src=PLACEHOLDER;};el.src=src;}
function initMap(){
  map=L.map('map',{minZoom:2,maxZoom:18});
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href=\\"https://www.openstreetmap.org/copyright\\">OpenStreetMap</a> contributors'}).addTo(map);
  const pts=[];
  stops.forEach(function(s,idx){
    L.marker([s.lat,s.lng]).addTo(map).bindTooltip('<b>'+(s.title||('Stop '+(idx+1)))+'</b>',{direction:'top',offset:[0,-30]}).on('click',function(){i=idx;show();});
    pts.push([s.lat,s.lng]);
  });
  if(pts.length>1)map.fitBounds(pts,{padding:[60,60]});else if(pts.length===1)map.setView(pts[0],stops[0].zoom||10);else map.setView([20,0],2);
  new ResizeObserver(function(){map.invalidateSize();}).observe(document.getElementById('map'));
}
function begin(){document.getElementById('intro').classList.add('gone');setTimeout(function(){document.getElementById('intro').style.display='none';},500);map.invalidateSize();i=0;show();}
function show(){
  const s=stops[i],z=s.zoom||10;
  loadImage(document.getElementById('p-img'),s.img);
  document.getElementById('p-img').alt=s.title||'';
  document.getElementById('p-title').textContent=s.title||'';
  document.getElementById('p-sub').textContent=s.sub||'';
  document.getElementById('p-text').textContent=s.text||'';
  document.getElementById('prog').textContent=(i+1)+' / '+stops.length;
  document.getElementById('back').style.visibility=i===0?'hidden':'visible';
  document.getElementById('panel-scroll').scrollTop=0;
  document.getElementById('panel').style.display='flex';
  if(window.matchMedia('(max-width:700px)').matches){const p=map.project([s.lat,s.lng],z);p.y+=map.getSize().y*0.26;map.flyTo(map.unproject(p,z),z,{duration:2});}
  else{map.flyTo([s.lat,s.lng],z,{duration:2});}
}
function next(){if(i<stops.length-1){i++;show();}else closePanel();}
function prev(){if(i>0){i--;show();}}
function closePanel(){document.getElementById('panel').style.display='none';}
document.getElementById('p-img').addEventListener('click',function(){if(this.src===PLACEHOLDER)return;document.getElementById('lb-img').src=this.src;document.getElementById('lb').classList.add('on');});
document.addEventListener('keydown',function(e){if(e.key==='Escape'){const lb=document.getElementById('lb');if(lb.classList.contains('on'))lb.classList.remove('on');else closePanel();}if(e.key==='ArrowRight')next();if(e.key==='ArrowLeft')prev();});
window.onload=initMap;
</script>
</body>
</html>
"""


def _standardize_into(sources, img_dir, args, dry, verb="add"):
    """Resize sources into img_dir; return list of output basenames in order."""
    if not dry:
        img_dir.mkdir(parents=True, exist_ok=True)
    names = []
    for p in sources:
        stem = slugify(p.stem)
        if dry:
            name = stem + ('.png' if p.suffix.lower() == '.png' else '.jpg')
            print(f"  would {verb}  images/{name}")
        else:
            o = process_image(p, img_dir / stem, args.max, args.quality)
            name = o.name
            print(f"  wrote  {name:<36} {o.stat().st_size/1024:6.0f} KB")
        names.append(name)
    return names


def main():
    ap = argparse.ArgumentParser(description="Image standardizer + tour builder.")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--tour", default=None)
    ap.add_argument("--map-tour", dest="map_tour", default=None)
    ap.add_argument("--site", default=None)
    ap.add_argument("--project", default=None)
    ap.add_argument("--max", type=int, default=1600)
    ap.add_argument("--quality", type=int, default=85)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = Path(os.path.expanduser(args.src)).resolve()
    if not src.is_dir():
        sys.exit(f"Source folder not found: {src}")
    sources = gather(src)
    if not sources:
        sys.exit(f"No images found in {src}")
    dry = args.dry_run

    # MODE A: standardize only
    if args.out:
        out_dir = Path(os.path.expanduser(args.out)).resolve()
        print(f"STANDARDIZE  {src}  ({len(sources)} images)  ->  {out_dir}"
              f"{'   (DRY RUN)' if dry else ''}\n")
        _standardize_into(sources, out_dir, args, dry, verb="write")
        print(f"\nDone. {len(sources)} image(s) standardized into {out_dir}. Nothing else touched.")
        return

    # MODE B: slideshow tour
    if args.tour:
        tour_path = Path(os.path.expanduser(args.tour)).resolve()
        img_dir = tour_path.parent / "images"
        print(f"BUILD SLIDESHOW  {src}  ({len(sources)} images)")
        print(f"   images -> {img_dir}")
        print(f"   html   -> {tour_path}{'   (DRY RUN)' if dry else ''}\n")
        names = _standardize_into(sources, img_dir, args, dry)
        slides = [{"image": f"images/{n}", "label": label_from_stem(p.stem), "caption": "TODO"}
                  for p, n in zip(sources, names)]
        if dry:
            print(f"\nWould write a slideshow of {len(slides)} images to {tour_path}."); return
        html = (SLIDESHOW_TEMPLATE
                .replace("__SLIDES__", json.dumps(slides, indent=2, ensure_ascii=False))
                .replace("__PLACEHOLDER__", _PLACEHOLDER_JS))
        tour_path.write_text(html, encoding="utf-8")
        print(f"\nDone. {len(slides)} images + a self-contained slideshow at {tour_path}.")
        print("Open it in your browser. Edit the `slides` list near the bottom to add captions and reorder.")
        return

    # MODE C: geographic map tour
    if args.map_tour:
        tour_path = Path(os.path.expanduser(args.map_tour)).resolve()
        img_dir = tour_path.parent / "images"
        print(f"BUILD MAP TOUR  {src}  ({len(sources)} images)")
        print(f"   images -> {img_dir}")
        print(f"   html   -> {tour_path}")
        print(f"   coords -> seeded from {len(DEFAULT_COORDS)} default points"
              f"{' (recycled)' if len(sources) > len(DEFAULT_COORDS) else ''}"
              f"{'   (DRY RUN)' if dry else ''}\n")
        names = _standardize_into(sources, img_dir, args, dry)
        stops = []
        for idx, (p, n) in enumerate(zip(sources, names)):
            c = DEFAULT_COORDS[idx % len(DEFAULT_COORDS)]
            stops.append({"lat": c["lat"], "lng": c["lng"], "zoom": c["zoom"],
                          "title": label_from_stem(p.stem), "sub": "TODO - place & date",
                          "img": f"images/{n}", "text": "TODO"})
        if dry:
            print(f"\nWould write a map tour of {len(stops)} stops to {tour_path}."); return
        html = (MAP_TOUR_TEMPLATE
                .replace("__STOPS__", json.dumps(stops, indent=2, ensure_ascii=False))
                .replace("__PLACEHOLDER__", _PLACEHOLDER_JS))
        tour_path.write_text(html, encoding="utf-8")
        print(f"\nDone. {len(stops)} images + a self-contained map tour at {tour_path}.")
        print("Open it in your browser. Pins sit on the seed coordinates until you edit the `stops` list.")
        return

    # MODE D: Learn More entry -> NEW json
    if not (args.site and args.project):
        sys.exit("Pick a mode: --out, --tour, --map-tour, or --site + --project.")
    project = Path(os.path.expanduser(args.project)).resolve()
    out_dir = project / "images" / args.site
    new_json = project / "data" / "learn-more.NEW.json"
    print(f"LEARN MORE  site '{args.site}'  ({len(sources)} images)")
    print(f"   images -> {out_dir}")
    print(f"   entry  -> {new_json}   (master learn-more.json NOT touched)")
    print(f"{'   (DRY RUN)' if dry else ''}\n")
    names = _standardize_into(sources, out_dir, args, dry, verb="write")
    steps = [{"image": f"images/{args.site}/{n}", "label": label_from_stem(p.stem), "caption": "TODO"}
             for p, n in zip(sources, names)]
    entry = {args.site: steps}
    if dry:
        print("\nWould write this block to learn-more.NEW.json:\n")
        print(json.dumps(entry, indent=2, ensure_ascii=False)); return
    new_json.parent.mkdir(parents=True, exist_ok=True)
    new_json.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote the new entry to {new_json.name}. Master learn-more.json NOT changed -")
    print(f"review it, then paste the '{args.site}' block into your master when ready.")


if __name__ == "__main__":
    main()
