#!/usr/bin/env python3
"""Build the published page from src/.

    python3 build.py           build index.html
    python3 build.py --check   verify index.html matches src/ (exit 1 if stale)

src/dashboard.html is the only file you edit. index.html at the repo root is
generated from it and overwritten on every build — GitHub Pages serves the repo root,
which is why the output has to land there rather than in a dist/ directory.

The build does three things:

  1. Inlines Chart.js and the Inter typeface from src/vendor/, replacing the CDN
     <link> and <script> tags. The page then has no network dependencies at all, so it
     renders identically offline, on a locked-down conference network, or opened
     straight off the filesystem. Both files are vendored into the repo rather than
     fetched at build time so a build is reproducible and does not depend on cdnjs or
     Google Fonts being reachable.

  2. Adds the metadata a shared link needs to render as a preview card — description,
     favicon, Open Graph and Twitter tags. The og:image is absolute because some
     scrapers will not resolve a relative one; BASE_URL below is where that comes from.

  3. Regenerates og-card.png from src/og-card.svg if a rasterizer is installed, and
     otherwise leaves the committed PNG alone and says so.
"""

import base64
import hashlib
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / 'src'

# Where the site is served from. Only used to make og:image absolute. Change this and
# rebuild if the site moves; nothing else in the page depends on it.
BASE_URL = 'https://hotdogvulkin.github.io/Roboro-Capstone/'

DESCRIPTION = (
    "How late does each state enact its budget? 651 state-fiscal-years, FY2015-FY2027, "
    "verified against primary sources — with a forward-looking risk model for FY2028."
)
TITLE = "State Budget Timing — All 50 States"

BANNER = ("<!-- GENERATED FILE — DO NOT EDIT.\n"
          "     Built from src/dashboard.html by build.py. Edits here are lost on the\n"
          "     next build. Edit the source and run: python3 build.py -->\n")

# The two tags the build replaces. Kept as exact strings so a change to either in the
# source fails loudly here rather than silently shipping a page that still hits a CDN.
FONT_TAGS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600'
    '&display=swap" rel="stylesheet">'
)
CHART_TAG = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/'
             'chart.umd.js"></script>')

# Matches the latin subset Google Fonts serves for this family.
UNICODE_RANGE = ("U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, "
                 "U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, "
                 "U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD")


def build_html() -> str:
    html = (SRC / 'dashboard.html').read_text()

    # --- font -------------------------------------------------------------
    if FONT_TAGS not in html:
        sys.exit('build: could not find the Google Fonts <link> tags in '
                 'src/dashboard.html — did the head change?')
    woff2 = base64.b64encode((SRC / 'vendor' / 'inter-latin.woff2').read_bytes()).decode()
    face = ("@font-face{font-family:'Inter';font-style:normal;font-weight:400 600;"
            f"font-display:swap;src:url(data:font/woff2;base64,{woff2}) "
            f"format('woff2');unicode-range:{UNICODE_RANGE}}}")
    html = html.replace(FONT_TAGS,
                        '<style>/* Inter (latin subset, variable 400-600), embedded so the\n'
                        '   page renders identically with no network. Google Fonts, SIL\n'
                        '   Open Font License 1.1 */\n' + face + '</style>')

    # --- Chart.js ---------------------------------------------------------
    if CHART_TAG not in html:
        sys.exit('build: could not find the Chart.js <script> tag in '
                 'src/dashboard.html — did the head change?')
    chart = (SRC / 'vendor' / 'chart.umd.js').read_text()
    html = html.replace(CHART_TAG,
                        '<script>/* Chart.js v4.4.1 — MIT. Embedded rather than loaded from\n'
                        '   a CDN so the Snapshot chart survives an offline demo. */\n'
                        + chart + '\n</script>')

    # --- metadata ---------------------------------------------------------
    # The real mark, lifted from src/vendor/roboro-logo.svg — the three shapes at the
    # left of the wordmark, in their original coordinates. viewBox frames them square
    # with padding. Was a hand-drawn four-dot approximation before the brand asset existed.
    favicon = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-16 16.5 96 96">'
        '<rect x="-16" y="16.5" width="96" height="96" rx="20" fill="#0B0614"/>'
        '<path fill="#F2EEF7" d="M47.7,64.7c8.8,0,16-7.2,16-16.1s-7.2-16.1-16-16.1'
        's-16,7.2-16,16.1S38.8,64.7,47.7,64.7z"/>'
        '<path fill="#E60058" d="M0,48.6c0,8.9,7.2,16.1,16,16.1V32.5C7.2,32.5,0,39.7,0,48.6z"/>'
        '<path fill="#F2EEF7" d="M16,112.5c8.8,0,16-7.2,16-16.1s-7.2-16.1-16-16.1'
        'S0,87.5,0,96.4S7.2,112.5,16,112.5z"/></svg>')
    fav = base64.b64encode(favicon.encode()).decode()
    meta = f'''<meta name="description" content="{DESCRIPTION}">
<meta name="author" content="Grant Garcia">
<meta name="color-scheme" content="dark">
<link rel="icon" href="data:image/svg+xml;base64,{fav}">
<meta property="og:type" content="website">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:site_name" content="Roboro">
<meta property="og:image" content="{BASE_URL}og-card.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{TITLE}">
<meta name="twitter:description" content="{DESCRIPTION}">
<meta name="twitter:image" content="{BASE_URL}og-card.png">'''
    html = html.replace('<title>', meta + '\n<title>', 1)

    for host in ('cdnjs.cloudflare.com', 'fonts.googleapis.com'):
        # The source comment mentioning the CDN is fine; a live tag is not.
        if re.search(r'(?:src|href)="https://' + re.escape(host), html):
            sys.exit(f'build: output still references {host}')

    return BANNER + html


def build_og() -> str:
    """Rasterize the link-preview card, if anything on this machine can."""
    svg, png = SRC / 'og-card.svg', ROOT / 'og-card.png'
    for exe, args in (('rsvg-convert', ['-w', '1200', '-h', '630', '-o', str(png), str(svg)]),
                      ('cairosvg', [str(svg), '-o', str(png), '-W', '1200', '-H', '630'])):
        if shutil.which(exe):
            subprocess.run([exe] + args, check=True)
            return f'og-card.png regenerated with {exe}'
    return ('og-card.png left as committed — no rasterizer found. '
            'To regenerate: brew install librsvg, then rerun.')


def main() -> None:
    check = '--check' in sys.argv
    html = build_html()
    out = ROOT / 'index.html'
    current = out.read_text() if out.exists() else ''

    if check:
        same = hashlib.sha256(current.encode()).digest() == hashlib.sha256(html.encode()).digest()
        print('index.html is up to date' if same
              else 'index.html is STALE — run: python3 build.py')
        sys.exit(0 if same else 1)

    out.write_text(html)
    src_size = (SRC / 'dashboard.html').stat().st_size
    print(f'built index.html  {src_size:,} -> {len(html):,} bytes')
    print(f'  og:image base   {BASE_URL}')
    print(f'  {build_og()}')


if __name__ == '__main__':
    main()
