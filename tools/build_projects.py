#!/usr/bin/env python3
"""Build the CVTA case-study pages and the projects page list.

Run from anywhere:   python3 tools/build_projects.py
(optionally:         python3 tools/build_projects.py --images "/path/to/02_Images")

What it does
  1. Reads the project list below (title, image folder(s), cv-arch.co.uk post
     slug(s) for the text, and categories).
  2. Picks and optimises images from the asset folder into
     images/projects/<slug>/ as WebP (hero, grid, wide, extras, card, thumb).
  3. Writes projects/<slug>.html for every project — Figma "Case Study Flow"
     1546-132 (desktop) and 1474-1791 (mobile).
  4. Rewrites the project grid (desktop) and list (mobile) in projects.html
     between the <!-- PROJECTS:… --> markers, with data-cats for the filter.

Text comes from tools/cv-arch-posts.json (a saved copy of the cv-arch.co.uk
WordPress posts), so the build works offline. To add or change a project,
edit PROJECTS below and re-run.
"""
import html
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_IMAGES = os.path.join(os.path.dirname(ROOT), '01_Assets.', '02_Images')

# Category keys → labels (also the projects-page filter pills, in this order).
CATEGORIES = [
    ('education', 'Education'),
    ('residential', 'Residential'),
    ('public', 'Public and Civic'),
    ('heritage', 'Heritage'),
    ('worship', 'Places of Worship'),
    ('exhibition', 'Exhibition Design'),
    ('masterplanning', 'Masterplanning'),
    ('landscape', 'Landscape'),
    ('southwark', 'Projects in Southwark'),
]
CAT_LABEL = dict(CATEGORIES)

E, R, P, H, X, M, L, S = ('01_Education ', '02_Residential', '03_Public and Civic', '04_Heritage',
                          '06_Exhibition Design', '07_Masterplanning', '08_Landscape',
                          '09_Projects in Southwark')

# slug, title, image folders, cv-arch post slugs (text, in order), categories,
# optional explicit image order (filenames) for the main slots.
PROJECTS = [
    ('sir-michael-snyder-building', 'Sir Michael Snyder Building', [f'{E}/Sir Michael Snyder Building'],
     ['sir-michael-snyder-building'], ['education', 'residential'],
     # Figma 1546-132: hero, tall, right-top, right-bottom, wide
     ['Brentwood_SMS_Elevation.jpeg', 'Brentwood_SMS_Detail2.jpeg', 'Brentwood_SMS_Courtyard.jpeg',
      'Brentwood_SMS_Common.jpeg', '  .jpeg']),   # sic: the common-room photo is named two spaces + .jpeg
    ('bellenden-primary-school', 'Bellenden Primary School', [f'{E}/Bellenden Primary School'],
     ['bellenden-primary-school'], ['education', 'southwark']),
    ('central-foundation-girls-school', 'Central Foundation Girls School', [f'{E}/CFGS - Central Foundation Girls School'],
     [], ['education']),
    ('notre-dame-school', 'Notre Dame School', [f'{E}/Notre Dame School'],
     ['notre-dame-school'], ['education', 'southwark']),
    ('westborough-primary-school', 'Westborough Primary School', [f'{E}/Westborough Primary School'],
     ['westborough-primary-school'], ['education']),
    ('churchill-college', 'Churchill College', [f'{R}/Churchill College', f'{R}/Project 1 Residential'],
     ['churchill-college', 'project-1-residential'], ['residential']),
    ('charter-school-bermondsey', 'Charter School Bermondsey', [f'{E}/Charter School Bermondsey'],
     ['charter-school-bermondsey'], ['education']),
    ('st-thomas-the-apostle-library', 'St Thomas the Apostle College Library',
     [f'{E}/St Thomas The Apostle School Sixth Form College Library'],
     ['st-thomas-the-apostle-school-sixth-form-college-library'], ['education']),
    ('brentwood-preparatory-school', 'Brentwood Preparatory School', [f'{E}/Brentwood Preparatory School Expansion'],
     ['brentwood-preparatory-school-expansion'], ['education']),
    ('brentwood-school-reception', 'Brentwood School Reception', [f'{E}/Brentwood School Reception'],
     ['brentwood-school-reception'], ['education']),
    ('brentwood-school-learning-resource-centre', 'Brentwood School Learning Resource Centre',
     [f'{E}/Brentwood School Learning Resource Centre'],
     ['brentwood-school-learning-resource-centre'], ['education', 'heritage']),
    ('brentwood-school-sixth-form-centre', 'Brentwood School Sixth Form Centre', [f'{E}/Brentwood School Sixth Form Centre'],
     ['brentwood-school-sixth-form-centre'], ['education', 'heritage']),
    ('streatham-and-clapham-high-school-phase-one', 'Streatham and Clapham High School: Phase One',
     [f'{E}/Streatham and Clapham High School Phase One'],
     ['streatham-and-clapham-high-school-first-phase'], ['education']),
    ('streatham-and-clapham-high-school-phase-two', 'Streatham and Clapham High School: Phase Two',
     [f'{E}/Streatham and Clapham High School Phase Two'],
     ['streatham-and-clapham-school'], ['education']),
    ('lyndhurst-primary-school', 'Lyndhurst Primary School', [f'{E}/Lyndhurst Primary School'],
     ['lyndhurstprimaryschool'], ['education', 'southwark']),
    ('sacred-heart-school', 'Sacred Heart Roman Catholic School', [f'{E}/Sacred Heart Roman Catholic School'],
     ['sacred-heart-catholic-school', 'sacred-heart-roman-catholic-school'], ['education', 'southwark', 'landscape']),
    ('krishna-avanti-primary-school-croydon', 'Krishna Avanti Primary School, Croydon', [f'{E}/Krishna Avanti Primary School'],
     ['krishna-avanti-primary-school-2'], ['education']),
    ('krishna-avanti-primary-school-harrow', 'Krishna-Avanti Primary School, Harrow', [f'{E}/Krishna-Avanti Primary School'],
     ['krishna-avanti-school', 'krishna-avanti-primary-school'], ['education', 'landscape']),
    ('broadway-school', 'Broadway School', [f'{E}/Broadway School'],
     ['broadway-school'], ['education']),
    ('westborough-cardboard-building', 'Westborough Cardboard Building', [f'{E}/Westborough Cardboard Building'],
     ['westborough-cardboard-building'], ['education']),
    ('lloyd-park-childrens-centre', 'Lloyd Park Children’s Centre', [f'{E}/Lloyd Park Childrens Centre'],
     ['lloyd-park-childrens-centre'], ['education']),
    ('ndna-neighbourhood-nursery', 'NDNA Neighbourhood Nursery', [f'{E}/NDNA Neighbourhood Nursery'],
     ['national-day-nurseries-association'], ['education']),
    ('village-neighbourhood-nursery', 'Village Neighbourhood Nursery', [f'{E}/Village Neighbourhood Nursery'],
     ['village-neighbourhood-nursery'], ['education']),
    ('lilliput', 'Lilliput', [f'{E}/Lilliput'],
     ['lilliput'], ['education']),
    ('clare-college-cambridge', 'Clare College, Cambridge', [f'{R}/Clare College Cambridge', f'{H}/Clare College Cambridge 2'],
     ['clare-college-cambridge'], ['residential', 'heritage']),
    ('st-chads-student-housing', 'St Chad’s Student Housing', [f'{R}/St Chads Student Housing'],
     ['st-chads-student-housing'], ['residential']),
    ('grove-lane', 'Grove Lane', [f'{R}/Grove Lane'],
     ['grove-lane-2'], ['residential', 'southwark']),
    ('north-west-cambridge', 'North West Cambridge', [f'{R}/North West Cambridge', f'{L}/North West Cambridge 2'],
     ['north-west-cambridge', 'north-west-cambridge-2'], ['residential', 'landscape']),
    ('takaungu-creek', 'Takaungu Creek', [f'{R}/Takaungu Creek'],
     ['takaungu-creek'], ['residential']),
    ('leigh-on-sea', 'Leigh-on-Sea', [f'{R}/Leigh On Sea'],
     ['leigh-on-sea-2'], ['residential']),
    ('cite-radieuse', 'Cité Radieuse', [f'{R}/Le Cite Radieuse'],
     ['le-cite-radieuse'], ['residential', 'heritage']),
    ('bhaktivedanta-manor', 'Bhaktivedanta Manor', [f'{P}/Bhaktivedanta Manor', f'{M}/Bhaktivedanta Manor 2'],
     ['bhaktivedanta-manor'], ['public', 'heritage', 'worship', 'masterplanning']),
    ('royal-london-hospital', 'Royal London Hospital', [f'{P}/Royal London Hospital'],
     ['royal-london-hospital'], ['public']),
    ('all-saints-church', 'All Saints Church', [f'{P}/All Saints Church'],
     ['all-saints-church'], ['public', 'heritage']),
    ('prittlewell-priory-museum', 'Prittlewell Priory Museum', [f'{P}/Prittlewell Priory Museum'],
     ['prittlewell-priory-museum'], ['public', 'heritage']),
    ('bellingham-gateway', 'Bellingham Gateway', [f'{P}/Bellingham Gateway'],
     ['bellingham-gateway'], ['public']),
    ('all-souls-church', 'All Souls Church', [f'{H}/All Souls'],
     ['all-souls'], ['heritage', 'worship']),
    ('st-martins-church', 'St Martin’s Church', [f'{H}/St Martins Church'],
     ['st-martins-church'], ['heritage', 'worship']),
    ('edward-the-confessor', 'Edward the Confessor', [f'{H}/Edward The Confessor'],
     ['edward-the-confessor'], ['heritage', 'worship']),
    ('kensal-house', 'Kensal House', [f'{H}/Kensal House'],
     ['kensal-house'], ['heritage']),
    ('winkleigh-airfield', 'Winkleigh Airfield', [f'{M}/Winkleigh Airfield'],
     ['winkleigh-airfield'], ['masterplanning']),
    ('rude-britannia', 'Rude Britannia', [f'{X}/Rude Britannia'],
     ['rude-britannia'], ['exhibition']),
    ('gothic-nightmares', 'Gothic Nightmares', [f'{X}/Gothic Nightmares'],
     ['gothic-nightmares-dsfsdf'], ['exhibition']),
    ('james-gillray', 'James Gillray: The Art of Caricature', [f'{X}/James Gillray The Art Of Caricature'],
     ['james-gillray-the-art-of-caricature'], ['exhibition']),
    ('thomas-girtin', 'Thomas Girtin and the Art of Watercolours', [f'{X}/Thomas Girtin And The Art Of Watercolours'],
     ['thomas-girtin-and-the-art-of-watercolours'], ['exhibition']),
    ('delaroche-and-lady-jane-grey', 'Delaroche and Lady Jane Grey', [f'{X}/Delaroche And Lady Jane Grey'],
     ['delarohe-and-lady-jane-grey'], ['exhibition']),
    ('the-magic-pencil', 'The Magic Pencil for the British Council', [f'{X}/The Magic Pencil For The British Council'],
     ['the-magic-pencil-for-the-british-council'], ['exhibition']),
    ('secret-tate-habi-tate', 'Secret Tate: Habi Tate', [f'{X}/Secret Tate Habi Tate'],
     ['secret-tate-habi-tate'], ['exhibition']),
    ('southwark-design-services-framework', 'Southwark Architect Design Services Framework',
     [f'{S}/Southwark Architect Design Services Framework'],
     ['southwark-architect-design-services-framework'], ['southwark']),
]

IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp')
MAX_EXTRAS = 6


def esc(s):
    return html.escape(s, quote=True)


def image_size(path):
    out = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', path],
                         capture_output=True, text=True).stdout
    w = re.search(r'pixelWidth: (\d+)', out)
    h = re.search(r'pixelHeight: (\d+)', out)
    return (int(w.group(1)), int(h.group(1))) if w and h else (0, 0)


def natural_key(name):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', name)]


def gather_images(images_root, folders):
    seen, files = set(), []
    for folder in folders:
        d = os.path.join(images_root, folder)
        if not os.path.isdir(d):
            print('  ! missing folder', folder)
            continue
        for name in sorted(os.listdir(d), key=natural_key):
            if name == '.DS_Store' or not name.lower().endswith(IMG_EXT):
                continue
            if name in seen:                      # same photo filed under two categories
                continue
            seen.add(name)
            path = os.path.join(d, name)
            w, h = image_size(path)
            if w and h:
                files.append({'name': name, 'path': path, 'w': w, 'h': h, 'ar': w / h})
    return files


def choose_slots(files, order=None):
    """hero / tall / right-top / right-bottom / wide + extras (Figma slots)."""
    pool = list(files)
    if order:
        picked = [next(f for f in pool if f['name'] == n) for n in order]
        rest = [f for f in pool if f not in picked]
        rest.sort(key=lambda f: -f['w'] * f['h'])
        return picked, rest[:MAX_EXTRAS]
    if not pool:
        return [], []
    landscape = [f for f in pool if f['ar'] >= 1.1] or pool
    hero = max(landscape, key=lambda f: f['w'] * f['h'])
    pool.remove(hero)
    slots = [hero]
    if len(pool) == 2:                                   # 3 images: hero + a side-by-side pair
        return slots + sorted(pool, key=lambda f: -f['w'] * f['h']), []
    if len(pool) >= 3:
        tall = min(pool, key=lambda f: f['ar'])           # most portrait → tall left
        pool.remove(tall)
        pool.sort(key=lambda f: -f['w'] * f['h'])
        right = pool[:2]
        pool = pool[2:]
        slots += [tall] + right
    if pool:
        wide = max(pool, key=lambda f: f['ar'])          # widest → panoramic strip
        pool.remove(wide)
        slots.append(wide)
    pool.sort(key=lambda f: -f['w'] * f['h'])
    return slots, pool[:MAX_EXTRAS]


def run_cwebp(cmd, src, dst):
    """cwebp can't read some JPEGs (e.g. CMYK print files) — fall back to an
    sRGB PNG copy made with sips, leaving the original untouched."""
    if subprocess.run(cmd + [src, '-o', dst], capture_output=True).returncode == 0:
        return
    tmp = dst + '.tmp.png'
    subprocess.run(['sips', '-s', 'format', 'png', '-m',
                    '/System/Library/ColorSync/Profiles/sRGB Profile.icc', src, '--out', tmp],
                   check=True, capture_output=True)
    try:
        subprocess.run(cmd + [tmp, '-o', dst], check=True, capture_output=True)
    finally:
        os.remove(tmp)


def to_webp(src, dst, long_side, q=78):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return
    w, h = image_size(src)
    cmd = ['cwebp', '-quiet', '-q', str(q), '-m', '6', '-metadata', 'none']
    if max(w, h) > long_side:
        cmd += ['-resize', str(long_side), '0'] if w >= h else ['-resize', '0', str(long_side)]
    run_cwebp(cmd, src, dst)


def to_webp_cover(src, dst, short_side, q=78):
    """For small thumbnails: resize so the SHORT side is short_side."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return
    w, h = image_size(src)
    cmd = ['cwebp', '-quiet', '-q', str(q), '-m', '6', '-metadata', 'none']
    if min(w, h) > short_side:
        cmd += ['-resize', str(short_side), '0'] if w <= h else ['-resize', '0', str(short_side)]
    run_cwebp(cmd, src, dst)


def completion_year(paragraphs):
    text = ' '.join(paragraphs)
    m = re.search(r'\bcompleted in (\d{4})\b', text, re.I) or re.search(r'\bwas completed in (\d{4})', text, re.I)
    return m.group(1) if m else None


# ── Page template ────────────────────────────────────────────────────────────
NAV = [('Home', 'index.html'), ('Projects', 'projects.html'), ('Studio', 'studio.html'),
       ('Awards', 'awards.html'), ('Contact', 'contact.html')]
BLOCKS = '''<div class="menu-blocks" aria-hidden="true">
      <div class="menu-blocks__row"><i></i><i></i><i></i><i></i><i></i></div>
      <div class="menu-blocks__row"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
      <div class="menu-blocks__row"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
    </div>'''


def nav_items(cls, arrow_cls, up):
    return '\n'.join(
        f'      <li><a href="{up}{href}" class="{cls}">{label}</a><a href="{up}{href}" class="{arrow_cls} {cls}" '
        f'tabindex="-1" aria-hidden="true"><img src="{up}images/menu-arrow.svg" alt=""></a></li>'
        for label, href in NAV)


def img_tag(src, alt, cls, eager=False):
    loading = 'eager' if eager else 'lazy'
    return f'<img class="{cls}" src="{src}" alt="{esc(alt)}" loading="{loading}" decoding="async">'


PAGE_CSS = '''
    @font-face {
      font-family: 'Rag Narrow';
      src: url('../fonts/Rag-NarrowRegular.otf') format('opentype');
      font-weight: normal;
      font-style: normal;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Rag Narrow', Arial, sans-serif;
      overflow-x: hidden;
      background: #2f9351;
    }
    .overlay {
      position: fixed; inset: 0;
      background: rgba(255,255,255,0.5);
      opacity: 0; pointer-events: none;
      transition: opacity 0.4s ease;
      z-index: 150;
    }
    .overlay.open { opacity: 1; pointer-events: auto; }
    #nav-rive-canvas {
      position: fixed; top: 24px; right: 24px;
      width: 40px; height: 40px;
      z-index: 200; cursor: pointer; display: block;
    }

    /* ── CASE STUDY — Figma "Case Study Flow" 1546-132 (desktop) / 1474-1791
       (mobile). Green page; side padding grows 24 → 234 like the other
       desktop pages; content starts 12px below the logo / arrow bar. ── */
    .cs {
      --side-pad: clamp(24px, calc(24px + (100vw - 768px) * 210 / 980), 234px);
      min-height: 100vh;
      background: #2f9351;
      color: #000;
      padding: 88px var(--side-pad) 48px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }
    .cs__head { display: flex; flex-direction: column; gap: 10px; }
    .cs__title {
      font-family: 'Rag Narrow', Arial, sans-serif;
      font-weight: normal;
      font-size: 64px;
      line-height: normal;
      letter-spacing: 1.92px;
    }
    .cs__rule { width: 100%; height: 2px; background: #000; }
    .cs__head .cs__rule { display: none; }        /* mobile only */
    .cs__img { display: block; width: 100%; height: 100%; object-fit: cover; }
    /* image boxes keep their Figma proportions — never stretch to the photo */
    .cs__hero, .cs__wide, .cs__grid > div, .cs__extras > div { overflow: hidden; min-height: 0; min-width: 0; }
    .cs__hero { width: 100%; aspect-ratio: 1280 / 968; }

    .cs__content { display: flex; flex-direction: column; gap: 12px; }
    /* tall image left, two stacked right (1280 × 1224 block) */
    .cs__grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
      gap: 12px;
      aspect-ratio: 1280 / 1224;
    }
    .cs__grid .cs__tall { grid-row: 1 / 3; }
    .cs__grid--pair { grid-template-rows: 1fr; aspect-ratio: 1280 / 606; }
    .cs__text {
      font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
      font-size: 16px;
      line-height: normal;
      letter-spacing: 0.48px;
    }
    .cs__wide { width: 100%; aspect-ratio: 1280 / 400; }
    .cs__extras {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .cs__extras > div { aspect-ratio: 634 / 605; }

    /* "See our case studies" — pill + yellow arrow, back to the projects page */
    .cs__more {
      display: flex; flex-direction: column; gap: 12px;
      text-decoration: none; color: #000;
    }
    .cs__more .cs__rule { display: none; }        /* mobile only */
    .cs__btn { display: inline-flex; align-items: center; gap: 12px; align-self: flex-start; }
    .cs__btn-label {
      background: #248043;
      border-radius: 48px;
      padding: 10px 16px;
      font-size: 16px;
      line-height: 24px;
      letter-spacing: 0.48px;
      white-space: nowrap;
      transition: filter 0.2s ease;
    }
    .cs__btn img { width: 44px; height: 44px; display: block; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
    .cs__more:hover .cs__btn-label { filter: brightness(0.94); }
    .cs__more:hover .cs__btn img { transform: rotate(-45deg); }

    /* C V T A letters across the foot of the page */
    .cs__letters { display: flex; justify-content: space-between; align-items: flex-start; }
    .cs__letters img { display: block; height: 65px; width: auto; }

    #cvta-loader {
      position: fixed; inset: 0; z-index: 10000;
      background: #fff;
      display: flex; align-items: center; justify-content: center;
      transition: opacity 450ms cubic-bezier(.4, 0, .2, 1);
    }
    #cvta-loader.is-done { opacity: 0; pointer-events: none; }
    #cvta-loader-canvas { width: min(30vw, 30vh, 240px); height: min(30vw, 30vh, 240px); display: block; }

    /* ═════════ MOBILE (≤ 500px) — Figma 1474-1791 ═════════ */
    .mobile-view { display: none; }
    @media (max-width: 500px) {
      .overlay, .nav-drawer, #cvta-loader { display: none !important; }
      .mobile-view { display: block; }
      .cs { padding: 24px 12px; }
      .cs__head { padding-top: 50px; gap: 10px; }  /* 40px arrow slot + 10 */
      .cs__title { font-size: 68px; line-height: 103px; letter-spacing: 2.04px; word-break: break-word; }
      .cs__head .cs__rule { display: block; margin-top: -4px; }  /* 6px under the title */
      .cs__hero { aspect-ratio: 369 / 427; }
      .cs__grid, .cs__grid--pair { display: flex; flex-direction: column; aspect-ratio: auto; }
      .cs__grid > div, .cs__extras > div, .cs__wide { aspect-ratio: 369 / 400; }
      .cs__grid .cs__tall { order: 1; }                /* Figma: right-top, tall, right-bottom */
      .cs__grid .cs__r2 { order: 2; }
      .cs__extras { grid-template-columns: 1fr; }
      .cs__more .cs__rule { display: block; }
      .cs__btn { gap: 10px; }
      .cs__btn-label { font-size: 20px; line-height: 30px; letter-spacing: 0.6px; }
      .cs__btn img { width: 50px; height: 50px; }
      .cs__letters img { height: auto; width: 15%; max-width: 59px; }
    }
'''


def page_html(p, up='../'):
    t = p['title']
    s = p['slots']
    imgdir = f'{up}images/projects/{p["slug"]}/'

    def box(cls, key, alt, eager=False):
        return f'<div class="{cls}">{img_tag(imgdir + key + ".webp", alt, "cs__img", eager)}</div>'

    parts = []
    if len(s) >= 4:
        parts.append('      <div class="cs__grid">\n'
                     f'        {box("cs__tall", "tall", t + " — detail")}\n'
                     f'        {box("cs__r1", "right-1", t)}\n'
                     f'        {box("cs__r2", "right-2", t)}\n'
                     '      </div>')
    elif len(s) == 3:
        parts.append('      <div class="cs__grid cs__grid--pair">\n'
                     f'        {box("cs__r1", "right-1", t)}\n'
                     f'        {box("cs__r2", "right-2", t)}\n'
                     '      </div>')
    if p['paragraphs']:
        paras = '\n'.join(f'        <p>{esc(x)}</p>' for x in p['paragraphs'])
        parts.append(f'      <div class="cs__text">\n{paras}\n      </div>')
    if p['has_wide']:
        parts.append(f'      {box("cs__wide", "wide", t)}')
    if p['extras']:
        ex = '\n'.join(f'        {box("", f"extra-{i + 1}", t)}' for i in range(p['extras']))
        parts.append(f'      <div class="cs__extras">\n{ex}\n      </div>')
    content = '\n'.join(parts)

    letters = ''.join(f'<img src="{up}images/case-study/letter-{c}.svg" alt="">' for c in 'cvta')
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{esc(t)} — Cottrell Vermeulen Tucker Architecture</title>
  <!-- Generated by tools/build_projects.py — edit the data there and re-run. -->
  <style>{PAGE_CSS}  </style>
  <link rel="stylesheet" href="{up}menu.css?v=22">

  <script defer src="https://unpkg.com/@rive-app/webgl2@2.43.1/rive.js"></script>
  <script defer src="{up}Rive/loader.js?v=2"></script>
  <script defer src="{up}Rive/menubar.js?v=9"></script>
</head>
<body>

  <div id="cvta-loader" aria-hidden="true">
    <canvas id="cvta-loader-canvas" width="960" height="960"></canvas>
  </div>

  <div class="overlay" id="overlay"></div>

  <nav class="nav-drawer" id="navDrawer">
    <a href="{up}index.html" class="nav-drawer__logo-box nav-link" aria-label="CVTA — home">
      <img src="{up}images/menu-logo-cvta.png" alt="">
    </a>
    <div class="nav-drawer__top"></div>
    <ul class="nav-drawer__menu">
{nav_items("nav-link", "nav-arrow", up)}
    </ul>
    {BLOCKS}
  </nav>

  <main class="cs">
    <header class="cs__head">
      <h1 class="cs__title">{esc(t)}</h1>
      <div class="cs__rule"></div>
      {box("cs__hero", "hero", t, eager=True)}
    </header>

    <section class="cs__content">
{content}
    </section>

    <a class="cs__more" href="{up}projects.html">
      <span class="cs__rule"></span>
      <span class="cs__btn">
        <span class="cs__btn-label">See our case studies</span>
        <img src="{up}images/case-study/arrow-44.svg" alt="">
      </span>
    </a>

    <div class="cs__letters" aria-hidden="true">{letters}</div>
  </main>

  <script>
    const overlay = document.getElementById('overlay');
    function setMenuOpen(open) {{
      document.documentElement.classList.toggle('menu-open', open);
      const m = document.getElementById('mNavDrawer');
      if (m) m.setAttribute('aria-hidden', String(!open));
    }}
    const closeDrawer = () => setMenuOpen(false);
    document.addEventListener('cvta:drawer-toggle', (e) => setMenuOpen(!!(e.detail && e.detail.open)));
    const closeViaRive = () => (window.CVTANav ? window.CVTANav.close() : closeDrawer());
    overlay.addEventListener('click', closeViaRive);
    document.addEventListener('DOMContentLoaded', () => {{
      document.querySelectorAll('.nav-link, .m-nav-link').forEach(l => l.addEventListener('click', closeViaRive));
      // Mobile button uses the 50px arrow (Figma 1474-1791).
      if (window.matchMedia('(max-width: 500px)').matches) {{
        document.querySelector('.cs__btn img').src = '{up}images/case-study/arrow-50.svg';
      }}
    }});
  </script>

  <a class="site-logo" href="{up}index.html" aria-label="CVTA — home"><img src="{up}images/web/cvta-logo-05.webp" alt=""></a>
  <canvas id="nav-rive-canvas" width="80" height="80" aria-label="Open menu"></canvas>

  <div class="mobile-view">
    <nav class="m-nav-drawer" id="mNavDrawer" aria-hidden="true">
      <div class="m-nav-drawer__top">
        <a href="{up}index.html" class="m-nav-drawer__logo m-nav-link" aria-label="CVTA — home"><img src="{up}images/menu-logo-cvta.png" alt=""></a>
      </div>
      <ul class="m-nav-drawer__menu">
{nav_items("m-nav-link", "m-nav-arrow", up)}
      </ul>
      {BLOCKS}
    </nav>
  </div>

</body>
</html>
'''


# ── Projects page list ───────────────────────────────────────────────────────
def projects_markup(projects):
    desk, mob = [], []
    for p in projects:
        cats = ' '.join(p['cats'])
        href = f'projects/{p["slug"]}.html'
        sub = p['year'] or CAT_LABEL[p['cats'][0]]
        desk.append(
            f'          <a class="project-card" href="{href}" data-cats="{cats}">\n'
            f'            <img class="project-card__img" src="images/projects/{p["slug"]}/card.webp" alt="{esc(p["title"])}" loading="lazy" decoding="async">\n'
            f'            <div class="project-card__info"><p class="project-card__name">{esc(p["title"])}</p>'
            f'<p class="project-card__year">{esc(sub)}</p></div>\n'
            f'          </a>')
        mob.append(
            f'      <li class="m-projects-item" data-cats="{cats}"><a href="{href}">\n'
            f'        <div class="m-projects-item__text">\n'
            f'          <span class="m-projects-item__name">{esc(p["title"])}</span>\n'
            f'          <span class="m-projects-item__year">{esc(sub)}</span>\n'
            f'        </div>\n'
            f'        <img class="m-projects-item__img" src="images/projects/{p["slug"]}/thumb.webp" alt="" loading="lazy" decoding="async">\n'
            f'      </a></li>')
    return '\n'.join(desk), '\n'.join(mob)


def pills_markup(indent):
    pills = [f'{indent}<button class="filter-pill is-selected" type="button" data-cat="all">All</button>']
    for i, (key, label) in enumerate(CATEGORIES, 1):
        pills.append(f'{indent}<button class="filter-pill" type="button" style="--i:{i}" data-cat="{key}">{label}</button>')
    return '\n'.join(pills)


def replace_between(text, name, body):
    a, b = f'<!-- PROJECTS:{name} -->', f'<!-- /PROJECTS:{name} -->'
    i, j = text.index(a) + len(a), text.index(b)
    return text[:i] + '\n' + body + '\n' + text[j:]


def main():
    images_root = DEFAULT_IMAGES
    if '--images' in sys.argv:
        images_root = sys.argv[sys.argv.index('--images') + 1]
    posts = json.load(open(os.path.join(ROOT, 'tools', 'cv-arch-posts.json')))

    built = []
    for entry in PROJECTS:
        slug, title, folders, post_slugs, cats = entry[:5]
        order = entry[5] if len(entry) > 5 else None
        print('•', title)
        paragraphs = []
        for ps in post_slugs:
            for para in posts.get(ps, {}).get('paragraphs', []):
                if para not in paragraphs:
                    paragraphs.append(para)
        files = gather_images(images_root, folders)
        slots, extras = choose_slots(files, order)
        if not slots:
            print('  ! no images — skipped')
            continue
        out = os.path.join(ROOT, 'images', 'projects', slug)
        names = ['hero']
        if len(slots) >= 4:
            names += ['tall', 'right-1', 'right-2']
        elif len(slots) == 3:
            names += ['right-1', 'right-2']
        has_wide = len(slots) in (2, 5) or len(slots) > 5
        if has_wide:
            names.append('wide')
        for f, n in zip(slots, names):
            to_webp(f['path'], os.path.join(out, n + '.webp'), 2000 if n in ('hero', 'wide') else 1400)
        for i, f in enumerate(extras):
            to_webp(f['path'], os.path.join(out, f'extra-{i + 1}.webp'), 1400)
        to_webp(slots[0]['path'], os.path.join(out, 'card.webp'), 1000)
        to_webp_cover(slots[0]['path'], os.path.join(out, 'thumb.webp'), 400)
        p = {'slug': slug, 'title': title, 'cats': cats, 'paragraphs': paragraphs,
             'slots': slots, 'has_wide': has_wide, 'extras': len(extras),
             'year': completion_year(paragraphs)}
        if not paragraphs:
            print('  ! no text found')
        os.makedirs(os.path.join(ROOT, 'projects'), exist_ok=True)
        with open(os.path.join(ROOT, 'projects', slug + '.html'), 'w') as fh:
            fh.write(page_html(p))
        built.append(p)

    # projects.html — grid, list and filter pills
    path = os.path.join(ROOT, 'projects.html')
    page = open(path).read()
    desk, mob = projects_markup(built)
    page = replace_between(page, 'grid', desk)
    page = replace_between(page, 'list', mob)
    page = replace_between(page, 'pills', pills_markup('              '))
    page = replace_between(page, 'm-pills', pills_markup('          '))
    open(path, 'w').write(page)
    print(f'\n{len(built)} case studies built; projects.html updated.')


if __name__ == '__main__':
    main()
