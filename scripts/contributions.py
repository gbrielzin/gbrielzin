"""Generate a clean contribution graph (light and dark SVG) from the GitHub API.

Usage: GITHUB_TOKEN=... python scripts/contributions.py <login> <out_dir>
"""
import datetime as dt
import json
import os
import sys
import urllib.request

QUERY = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}"""

THEMES = {
    "light": {"bg": "#ffffff", "text": "#1f2328", "muted": "#656d76", "border": "#d0d7de",
              "scale": ["#eef2f6", "#c6dbf7", "#8ab8f0", "#3f87e0", "#1a5fb4"]},
    "dark": {"bg": "#0d1117", "text": "#e6edf3", "muted": "#8b949e", "border": "#30363d",
             "scale": ["#161b22", "#16325c", "#1f5aa6", "#3f87e0", "#8ab8f0"]},
}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
CELL, GAP, LEFT, TOP = 11, 3, 32, 74


def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"u": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", body,
                                 {"Authorization": f"bearer {token}", "User-Agent": login})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level(count, cuts):
    if count == 0:
        return 0
    return 1 + sum(count > c for c in cuts)


def stats(days):
    active = sum(d["contributionCount"] > 0 for d in days)
    best = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        best = max(best, run)
    current = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            current += 1
        elif current or d is not days[-1]:  # today may still be empty
            break
    return active, best, current


def render(cal, theme):
    t = THEMES[theme]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    nonzero = sorted(d["contributionCount"] for d in days if d["contributionCount"])
    cuts = [nonzero[int(len(nonzero) * q)] for q in (0.25, 0.5, 0.75)] if nonzero else [0, 0, 0]
    active, best, current = stats(days)
    width = LEFT + len(weeks) * (CELL + GAP) + 16
    height = TOP + 7 * (CELL + GAP) + 36
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
           f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
           f'fill="{t["bg"]}" stroke="{t["border"]}"/>',
           f'<text x="{LEFT}" y="30" font-size="15" font-weight="600" fill="{t["text"]}">'
           f'{cal["totalContributions"]:,} contributions in the last year</text>',
           f'<text x="{LEFT}" y="50" font-size="12" fill="{t["muted"]}">'
           f'longest streak {best} days · current streak {current} days · updated daily</text>']
    last_month = None
    for i, w in enumerate(weeks):
        x = LEFT + i * (CELL + GAP)
        first = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last_month and i < len(weeks) - 1:
            if last_month is not None or first.day <= 7:
                out.append(f'<text x="{x}" y="{TOP - 6}" font-size="10" fill="{t["muted"]}">'
                           f'{MONTHS[first.month - 1]}</text>')
            last_month = first.month
        for d in w["contributionDays"]:
            y = TOP + d["weekday"] * (CELL + GAP)
            c = d["contributionCount"]
            out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                       f'fill="{t["scale"][level(c, cuts)]}"><title>{c} on {d["date"]}</title></rect>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="8" y="{TOP + row * (CELL + GAP) + 9}" font-size="9" '
                   f'fill="{t["muted"]}">{name}</text>')
    ly = height - 20
    lx = width - 16 - 5 * (CELL + GAP) - 58
    out.append(f'<text x="{lx}" y="{ly + 9}" font-size="10" fill="{t["muted"]}">Less</text>')
    for k, color in enumerate(t["scale"]):
        out.append(f'<rect x="{lx + 28 + k * (CELL + GAP)}" y="{ly}" width="{CELL}" '
                   f'height="{CELL}" rx="2.5" fill="{color}"/>')
    out.append(f'<text x="{lx + 32 + 5 * (CELL + GAP)}" y="{ly + 9}" font-size="10" '
               f'fill="{t["muted"]}">More</text>')
    out.append('</svg>')
    return "\n".join(out)


def main():
    login, out_dir = sys.argv[1], sys.argv[2]
    cal = fetch(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"contributions-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(cal, theme))


if __name__ == "__main__":
    main()
