"""Generate assets/contributions.svg - a contribution heatmap in the ITLG palette.

Reads the public contribution calendar of a GitHub user (no token needed) and
renders a self-contained animated SVG card.

Usage: python scripts/gen_heatmap.py [username]
"""
import html
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else "yopalll"
OUT = Path(__file__).resolve().parent.parent / "assets" / "contributions.svg"

# ITLG palette -> contribution levels (0 = none ... 4 = most)
LEVELS = ["#2B2B2B", "#770707", "#A81515", "#DF3232", "#F26B6B"]
CELL, GAP = 14, 3
PITCH = CELL + GAP
X0, Y0 = 62, 58
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch(user: str) -> str:
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "Mozilla/5.0 (heatmap-generator)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse(page: str):
    total_match = re.search(r"([\d,]+)\s+contributions\s+in the last year", page)
    total = total_match.group(1) if total_match else "0"

    # tooltips carry the exact count per cell, keyed by the cell id
    counts = {}
    for cell_id, text in re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)</tool-tip>', page):
        m = re.match(r"(\d+)\s+contribution", text.strip())
        counts[cell_id] = int(m.group(1)) if m else 0

    cells = []
    for tag in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", page):
        cid = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', tag)
        d = re.search(r'data-date="([\d-]+)"', tag)
        lvl = re.search(r'data-level="(\d)"', tag)
        if not (cid and d and lvl):
            continue
        row, col = int(cid.group(1)), int(cid.group(2))
        cells.append((row, col, d.group(1), int(lvl.group(1)), counts.get(f"contribution-day-component-{row}-{col}", 0)))
    return total, cells


def render(total: str, cells) -> str:
    cols = max(c[1] for c in cells) + 1
    width = X0 + cols * PITCH + 34
    height = 252
    out = []
    w = out.append
    w(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(total)} contributions in the last year">')
    w("<defs>")
    w('<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#1E1E1E"/><stop offset="100%" stop-color="#2A0707"/></linearGradient>')
    w('<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    w("<style>")
    w(".d{animation:pop .5s ease-out backwards}")
    w("@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}")
    w(".d{transform-box:fill-box;transform-origin:center}")
    w(".t{font:600 12px 'Segoe UI',Arial,sans-serif;fill:#989898}")
    w(".n{font:800 18px 'Segoe UI',Arial,sans-serif;fill:#FFFFFF}")
    w(".s{font:500 13px 'Segoe UI',Arial,sans-serif;fill:#E6E6E6}")
    w("</style></defs>")
    w(f'<rect width="{width}" height="{height}" rx="16" fill="url(#bg)" stroke="#989898" stroke-opacity="0.25"/>')

    # month labels
    last_month = None
    for row, col, d, lvl, cnt in sorted(cells, key=lambda c: (c[1], c[0])):
        if row != 0:
            continue
        month = int(d.split("-")[1])
        if month != last_month:
            if col < cols - 2 or last_month is None:
                w(f'<text class="t" x="{X0 + col * PITCH}" y="{Y0 - 14}">{MONTHS[month - 1]}</text>')
            last_month = month

    # weekday labels
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        w(f'<text class="t" x="{X0 - 12}" y="{Y0 + row * PITCH + 11}" text-anchor="end">{name}</text>')

    # cells
    for row, col, d, lvl, cnt in cells:
        x, y = X0 + col * PITCH, Y0 + row * PITCH
        color = LEVELS[min(lvl, 4)]
        extra = ' filter="url(#glow)"' if lvl == 4 else ""
        label = f"{cnt} contribution{'s' if cnt != 1 else ''} on {d}"
        w(f'<rect class="d" style="animation-delay:{col * 0.03:.2f}s" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{color}"{extra}><title>{label}</title></rect>')

    # footer: total + legend
    fy = Y0 + 7 * PITCH + 34
    w(f'<text class="n" x="{X0 - 34}" y="{fy}">{html.escape(total)}</text>')
    w(f'<text class="s" x="{X0 - 34 + 14 + 10 * len(total)}" y="{fy}">contributions in the last year</text>')
    lx = width - 34 - (5 * PITCH) - 74
    w(f'<text class="t" x="{lx}" y="{fy - 1}">Less</text>')
    for i, c in enumerate(LEVELS):
        w(f'<rect x="{lx + 32 + i * PITCH}" y="{fy - 12}" width="{CELL}" height="{CELL}" rx="3" fill="{c}"/>')
    w(f'<text class="t" x="{lx + 32 + 5 * PITCH + 4}" y="{fy - 1}">More</text>')
    w(f'<text class="t" x="{X0 - 34}" y="{height - 14}" opacity="0.7">updated {date.today().isoformat()} &#183; @{USER}</text>')
    w("</svg>")
    return "\n".join(out)


def main():
    total, cells = parse(fetch(USER))
    if not cells:
        sys.exit("No contribution cells found - GitHub markup may have changed.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(total, cells), encoding="utf-8")
    print(f"wrote {OUT} ({len(cells)} cells, {total} contributions)")


if __name__ == "__main__":
    main()
