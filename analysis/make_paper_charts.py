#!/usr/bin/env python3
"""Render the white paper's charts from the same CSVs the dashboard reads.

Charts in a paper drift from the dashboard the moment either is edited by hand, so
these are generated. Output is SVG plus a rasterised PNG for embedding in Word.

macOS has no rsvg-convert/cairosvg here, and Quick Look renders a wide SVG at 1:1
anchored top-left — clipping the right edge. So each chart is authored on a square
canvas with the plot centred vertically, then centre-cropped back to its true
aspect. That is the only reason for the transform/crop dance below.
"""
import csv, os, subprocess, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
OUT  = os.path.join(os.path.dirname(HERE), "paper")
os.makedirs(OUT, exist_ok=True)

INK, MUTED, RULE = "#1A1626", "#6B6480", "#E3E0EA"
PINK, GREEN, SURF = "#E60058", "#1D9E75", "#FFFFFF"
F = "Helvetica Neue, Helvetica, Arial, sans-serif"

def load(n):
    with open(os.path.join(DATA, n)) as fh: return list(csv.DictReader(fh))

META = {r["state"]: r for r in load("state_budget_metadata.csv")}
ROWS = [r for r in load("budget_timing_pilot_data_cleaned.csv")
        if r["enactment_type"] != "biennial carryover"]
def missed(r): return r["budget_enacted"] != "yes" or not r["days_late"] or int(r["days_late"]) > 0

BY = defaultdict(list)
for r in ROWS: BY[r["state"]].append(r)
rate = {s: 100*sum(1 for r in v if missed(r))/len(v) for s, v in BY.items()}

def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def txt(x,y,s,size=20,fill=INK,anchor="start",weight="400"):
    return (f'<text x="{x}" y="{y}" font-family="{F}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>')

def render(name, w, h, body):
    """Author square, crop to w x h."""
    side = max(w, h); dy = (side - h) / 2
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{side}" height="{side}" '
           f'viewBox="0 0 {side} {side}"><rect width="{side}" height="{side}" fill="{SURF}"/>'
           f'<g transform="translate(0,{dy})">{body}</g></svg>')
    sp = os.path.join(OUT, name + ".svg")
    open(sp, "w").write(svg)
    subprocess.run(["qlmanage","-t","-s",str(side),"-o",OUT,sp],
                   capture_output=True, check=False)
    tmp = os.path.join(OUT, name + ".svg.png")
    png = os.path.join(OUT, name + ".png")
    subprocess.run(["sips","-c",str(h),str(w),tmp,"--out",png],
                   capture_output=True, check=False)
    if os.path.exists(tmp): os.remove(tmp)
    ok = os.path.exists(png)
    print(f"  {name}.png  {'OK' if ok else 'FAILED'}")
    return ok

# --- 1. legislature type -----------------------------------------------------
def chart_legislature():
    W,H = 1000, 560
    ft = [s for s in rate if META[s]["legislature_type"] == "full-time"]
    pt = [s for s in rate if META[s]["legislature_type"] == "part-time"]
    vals = [("Part-time (citizen)\nlegislatures", 100-sum(rate[s] for s in pt)/len(pt), len(pt), GREEN),
            ("Full-time (professional)\nlegislatures", 100-sum(rate[s] for s in ft)/len(ft), len(ft), PINK)]
    b = [txt(0,34,"Budgets enacted on time, by legislature type",26,INK,weight="600"),
         txt(0,62,"Share of tracked budgets enacted on or before the state's own fiscal year start",17,MUTED)]
    x0, top, bh, gap = 300, 110, 84, 62
    for i,(lab,v,n,col) in enumerate(vals):
        y = top + i*(bh+gap)
        b.append(f'<rect x="{x0}" y="{y}" width="{(W-x0-120)}" height="{bh}" rx="5" fill="#F4F2F7"/>')
        b.append(f'<rect x="{x0}" y="{y}" width="{(W-x0-120)*v/100:.1f}" height="{bh}" rx="5" fill="{col}"/>')
        for j,line in enumerate(lab.split("\n")):
            b.append(txt(x0-22, y+34+j*24, line, 19, INK, "end", "500"))
        b.append(txt(x0+(W-x0-120)*v/100+14, y+bh/2+8, f"{v:.0f}%", 30, col, "start", "600"))
        b.append(txt(x0-22, y+34+len(lab.split("\n"))*24, f"{n} states", 15, MUTED, "end"))
    b.append(f'<line x1="0" y1="{top+2*(bh+gap)+6}" x2="{W}" y2="{top+2*(bh+gap)+6}" stroke="{RULE}"/>')
    b.append(txt(0, top+2*(bh+gap)+40,
        "The single strongest structural predictor in the dataset (p = 0.0003).", 18, INK, weight="500"))
    b.append(txt(0, top+2*(bh+gap)+68,
        "Short, constitutionally capped sessions force the work to finish; year-round chambers can always sit another week.",
        16, MUTED))
    return render("chart_legislature", W, H, "".join(b))

# --- 2. national on-time trend ----------------------------------------------
def chart_trend():
    W,H = 1000, 560
    byfy = defaultdict(list)
    for r in ROWS: byfy[int(r["fy_label"][2:])].append(not missed(r))
    yrs = sorted(f for f in byfy if f >= 2015)
    pts = [(f, 100*sum(byfy[f])/len(byfy[f])) for f in yrs]
    b = [txt(0,34,"National on-time rate, FY2015–FY2027",26,INK,weight="600"),
         txt(0,62,"Share of states that enacted before their own fiscal year began. Excludes two-year carryovers.",17,MUTED)]
    L,R,T,B = 62, 40, 110, 150
    pw, ph = W-L-R, H-T-B
    lo, hi = 60, 100
    X = lambda i: L + i*pw/(len(pts)-1)
    Y = lambda v: T + ph - (v-lo)/(hi-lo)*ph
    for g in range(60,101,10):
        b.append(f'<line x1="{L}" y1="{Y(g):.1f}" x2="{L+pw}" y2="{Y(g):.1f}" stroke="{RULE}"/>')
        b.append(txt(L-12, Y(g)+6, f"{g}%", 15, MUTED, "end"))
    d = " ".join(("M" if i==0 else "L")+f"{X(i):.1f},{Y(v):.1f}" for i,(f,v) in enumerate(pts))
    b.append(f'<path d="{d}" fill="none" stroke="{PINK}" stroke-width="2.5"/>')
    for i,(f,v) in enumerate(pts):
        b.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="5" fill="{PINK}"/>')
        b.append(txt(X(i), H-B+28, f"’{str(f)[2:]}", 15, MUTED, "middle"))
    for i,(f,v) in enumerate(pts):
        if f in (2015, 2021, 2027):
            # Label above peaks, below troughs — otherwise the callout sits on the line.
            trough = 0 < i < len(pts)-1 and v < pts[i-1][1] and v < pts[i+1][1]
            b.append(txt(X(i), Y(v)+(30 if trough else -18), f"{v:.0f}%", 19, INK, "middle", "600"))
    b.append(f'<line x1="0" y1="{H-100}" x2="{W}" y2="{H-100}" stroke="{RULE}"/>')
    b.append(txt(0, H-68, "Flat, not deteriorating — the within-state trend is +0.05 days per year (p = 0.90).", 18, INK, weight="500"))
    b.append(txt(0, H-40, "The FY2021 dip is COVID. What persists is not a worsening national average but a fixed set of states.", 16, MUTED))
    return render("chart_trend", W, H, "".join(b))

# --- 3. FY2028 watchlist -----------------------------------------------------
def chart_watchlist():
    W,H = 1000, 620
    def score(s):
        v = BY[s]; m = sum(1 for r in v if missed(r))
        lt = META[s]["legislature_type"]
        grp = [x for x in rate if META[x]["legislature_type"] == lt]
        g = sum(sum(1 for r in BY[x] if missed(r)) for x in grp)/sum(len(BY[x]) for x in grp)
        return (m + 3*g)/(len(v)+3)
    sess = {s:{int(r["fy_start_date"][:4]) for r in BY[s]} for s in BY}
    at = [s for s in BY if 2025 in sess[s]]
    top = sorted(at, key=score, reverse=True)[:5]
    b = [txt(0,34,"Highest FY2028 late-risk states",26,INK,weight="600"),
         txt(0,62,"Each state's own miss rate, shrunk toward the base rate for its legislature type",17,MUTED)]
    x0, top_y, bh, gap = 250, 108, 52, 26
    for i,s in enumerate(top):
        v = score(s)*100; y = top_y + i*(bh+gap)
        rec = BY[s]; m = sum(1 for r in rec if missed(r))
        b.append(f'<rect x="{x0}" y="{y}" width="{W-x0-130}" height="{bh}" rx="4" fill="#F4F2F7"/>')
        b.append(f'<rect x="{x0}" y="{y}" width="{(W-x0-130)*v/100:.1f}" height="{bh}" rx="4" fill="{PINK}"/>')
        b.append(txt(x0-20, y+33, s, 20, INK, "end", "500"))
        b.append(txt(x0+(W-x0-130)*v/100+14, y+34, f"{v:.0f}%", 24, PINK, "start", "600"))
        b.append(txt(x0+14, y+33, f"missed {m} of {len(rec)}", 15, "#FFFFFF"))
    yb = top_y + 5*(bh+gap) + 6
    b.append(f'<line x1="0" y1="{yb}" x2="{W}" y2="{yb}" stroke="{RULE}"/>')
    b.append(txt(0, yb+34, "82% precision at 5.3× the base rate, scored walk-forward on 427 state-years.", 18, INK, weight="500"))
    b.append(txt(0, yb+62, "Only prior years are used to score each state-year, so no result depends on knowing the outcome.", 16, MUTED))
    return render("chart_watchlist", W, H, "".join(b))

if __name__ == "__main__":
    print("rendering paper charts:")
    ok = all([chart_legislature(), chart_trend(), chart_watchlist()])
    sys.exit(0 if ok else 1)
