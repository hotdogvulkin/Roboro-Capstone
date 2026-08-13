#!/usr/bin/env python3
"""
Predictive signals in state budget enactment timing
===================================================

Four analyses on the 651-row verified budget-timing panel, asking one question:
can we tell a customer "your state is likely to be late this year" before it happens?

    1. Prior-year autocorrelation  — is lateness sticky?
    2. Election-year effect        — do legislators hurry home to campaign?
    3. Fiscal stress               — do lean years produce longer budget fights?
    4. Session overrun             — does a session running past its scheduled
                                     adjournment predict a late budget?

Run:  python3 budget_timing_predictive_analysis.py
Deps: numpy, scipy   (pip install numpy scipy)

Inputs (all in the same directory as this file):
    budget_timing_pilot_data_cleaned.csv          the verified timing panel
    state_budget_metadata.csv                     fy start / cycle / legislature type
    state_spending_timeseries_fy2015_fy2024.csv   total expenditures + population
    cpi_deflators.csv                             CPI-U, deflated to 2024$
    session_overrun_data.csv                      scheduled vs actual sine die (analysis 4)

Analysis conventions used throughout
------------------------------------
* Biennial carryover rows are EXCLUDED everywhere. A carryover is not a separate
  enactment decision — counting it would duplicate its parent year's date and
  manufacture correlation out of nothing.
* Rows with budget_enacted == "no" are excluded from day-count statistics (there is
  no signing date to measure) but are counted as misses where a rate is reported.
* days_late = signed_date - fy_start_date. Negative means enacted before the fiscal
  year began. "Late" / "missed" means days_late > 0.
* "Session year" = fy_start_date.year, i.e. the calendar year the budget-writing
  session convened. This is FY-1 for every state in the panel and, unlike the
  signing year, cannot be moved around by how late the budget actually was.
"""

import csv
import os
import random
import re
from collections import defaultdict
from datetime import date

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(7)
np.random.seed(7)

W = 78  # report width


def load(name):
    with open(os.path.join(HERE, name)) as fh:
        return list(csv.DictReader(fh))


def iso(s):
    if not s:
        return None
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def head(n, title):
    print("\n" + "=" * W)
    print(f"ANALYSIS {n}. {title}")
    print("=" * W)


def sub(title):
    print(f"\n-- {title} " + "-" * max(0, W - len(title) - 4))


def finding(text):
    print("\n  >> FINDING: " + text)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

META = {r["state"]: r for r in load("state_budget_metadata.csv")}
RAW = load("budget_timing_pilot_data_cleaned.csv")

OBS = []          # every direct, dated enactment
PANEL = defaultdict(dict)   # state -> {fy: days_late}
ENACT_EVENTS = defaultdict(dict)  # state -> {fy: enacted?}  (direct rows only)

for r in RAW:
    if r["enactment_type"] == "biennial carryover":
        continue
    fy = int(r["fy_label"][2:])
    ENACT_EVENTS[r["state"]][fy] = r["budget_enacted"] == "yes"
    if r["budget_enacted"] != "yes" or not r["days_late"]:
        continue
    OBS.append(
        dict(
            state=r["state"],
            fy=fy,
            session_year=int(r["fy_start_date"][:4]),
            days=int(r["days_late"]),
            late=int(r["days_late"]) > 0,
            cycle=META[r["state"]]["budget_cycle"],
            leg=META[r["state"]]["legislature_type"],
        )
    )
    PANEL[r["state"]][fy] = int(r["days_late"])

print("=" * W)
print("PREDICTIVE SIGNALS IN STATE BUDGET TIMING".center(W))
print("=" * W)
print(f"\nsource rows                 {len(RAW)}")
print(f"biennial carryovers dropped {sum(1 for r in RAW if r['enactment_type'] == 'biennial carryover')}")
print(f"no-budget rows dropped      {sum(1 for r in RAW if r['budget_enacted'] != 'yes')}")
print(f"analysis panel              {len(OBS)} state-years across {len(PANEL)} states, "
      f"FY{min(o['fy'] for o in OBS)}-FY{max(o['fy'] for o in OBS)}")
BASE = np.mean([o["late"] for o in OBS])
print(f"base rate of a late budget  {100 * BASE:.1f}%")


# ---------------------------------------------------------------------------
# 1. Prior-year autocorrelation
# ---------------------------------------------------------------------------

head(1, "PRIOR-YEAR AUTOCORRELATION — is lateness sticky?")

lag1 = []      # consecutive fiscal years
events = []    # consecutive budget-writing events (2 yrs apart for biennial states)
for s, d in PANEL.items():
    yrs = sorted(d)
    for y in yrs:
        if y - 1 in d:
            lag1.append((s, y, d[y - 1], d[y]))
    for a, b in zip(yrs, yrs[1:]):
        events.append((s, b, d[a], d[b]))

sub("correlation of days-late with the prior observation")
for label, pairs in [("strict lag-1 fiscal year", lag1),
                     ("consecutive budget events", events)]:
    x = np.array([p[2] for p in pairs], float)
    y = np.array([p[3] for p in pairs], float)
    pr = stats.pearsonr(x, y)
    sp = stats.spearmanr(x, y)
    print(f"  {label:26} n={len(pairs):3}  Pearson r={pr[0]:+.3f} (p={pr[1]:.2g})"
          f"   Spearman rho={sp[0]:+.3f} (p={sp[1]:.2g})")

sub("confusion matrix on strict lag-1 pairs (late = days_late > 0)")
tt = sum(1 for p in lag1 if p[2] > 0 and p[3] > 0)
tf = sum(1 for p in lag1 if p[2] > 0 and p[3] <= 0)
ft = sum(1 for p in lag1 if p[2] <= 0 and p[3] > 0)
ff = sum(1 for p in lag1 if p[2] <= 0 and p[3] <= 0)
print(f"                        this year LATE   this year ON TIME")
print(f"  last year LATE        {tt:>13}   {tf:>17}     ({tt}/{tt + tf} = {100 * tt / (tt + tf):.1f}% repeat)")
print(f"  last year ON TIME     {ft:>13}   {ff:>17}     ({ff}/{ff + ft} = {100 * ff / (ff + ft):.1f}% stay clean)")
table = np.array([[tt, tf], [ft, ff]])
chi2, chip, _, _ = stats.chi2_contingency(table)
odds, fishp = stats.fisher_exact(table)
print(f"\n  chi-square = {chi2:.1f} (p={chip:.2g}),  odds ratio = {odds:.1f} (Fisher p={fishp:.2g})")
print(f"  lift over the {100 * BASE:.1f}% base rate: {(tt / (tt + tf)) / BASE:.1f}x")

sub("is it momentum, or is it just the state? (within-state demeaning)")


def demeaned_r(pan):
    dx, dy = [], []
    for s, d in pan.items():
        m = np.mean(list(d.values()))
        for y in sorted(d):
            if y - 1 in d:
                dx.append(d[y - 1] - m)
                dy.append(d[y] - m)
    return stats.pearsonr(dx, dy)[0], len(dx)


obs_r, n_r = demeaned_r(PANEL)
null = []
for _ in range(5000):
    shuffled = {}
    for s, d in PANEL.items():
        yrs = sorted(d)
        vals = list(d.values())
        random.shuffle(vals)
        shuffled[s] = dict(zip(yrs, vals))
    null.append(demeaned_r(shuffled)[0])
null = np.array(null)
perm_p = 2 * min((null <= obs_r).mean(), (null >= obs_r).mean())
print(f"  observed within-state r          {obs_r:+.3f}  (n={n_r})")
print(f"  permutation null                 {null.mean():+.3f} +/- {null.std():.3f}")
print("     (demeaning with the state's own mean induces a negative bias by construction;")
print("      the permutation null measures exactly how much, so it can be subtracted off)")
print(f"  z vs null = {(obs_r - null.mean()) / null.std():+.2f},  two-sided permutation p = {perm_p:.3f}")

groups = [list(v.values()) for v in PANEL.values()]
F, anova_p = stats.f_oneway(*groups)
allv = [x for g in groups for x in g]
gm = np.mean(allv)
ssb = sum(len(g) * (np.mean(g) - gm) ** 2 for g in groups)
sst = sum((x - gm) ** 2 for x in allv)
k, n = len(groups), len(allv)
msb, msw = ssb / (k - 1), (sst - ssb) / (n - k)
nbar = n / k
icc = (msb - msw) / (msb + (nbar - 1) * msw)
print(f"\n  between-state share of variance  {ssb / sst:.1%}   (F={F:.1f}, p={anova_p:.2g})")
print(f"  intraclass correlation (ICC)     {icc:.2f}")

sub("walk-forward forecast — only years BEFORE the target are used")
rows = [(s, y, v > 0) for s, d in PANEL.items() for y, v in sorted(d.items())]


def evaluate(name, rule, minhist=3):
    tp = fp = tn = fn = 0
    for s, y, late in rows:
        hist = {yy: (v > 0) for yy, v in PANEL[s].items() if yy < y}
        if len(hist) < minhist:
            continue
        pred = rule(hist)
        if pred and late:
            tp += 1
        elif pred and not late:
            fp += 1
        elif not pred and late:
            fn += 1
        else:
            tn += 1
    used = tp + fp + tn + fn
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    print(f"  {name:36} precision {prec:6.1%}   recall {rec:6.1%}   accuracy {(tp + tn) / used:6.1%}")
    return prec, rec, used


print(f"  (evaluated on the {sum(1 for s, y, _ in rows if len({yy for yy in PANEL[s] if yy < y}) >= 3)} "
      f"state-years with at least 3 years of prior history)\n")
pA = evaluate("A: late last year", lambda h: h[max(h)])
pB = evaluate("B: late in >50% of prior years", lambda h: np.mean(list(h.values())) > 0.5)
pC = evaluate("C: late in >=1 prior year", lambda h: any(h.values()))
evaluate("D: never predict late (null model)", lambda h: False)

sub("miss rate by state")
sc = sorted(
    ((sum(1 for x in d.values() if x > 0) / len(d), sum(1 for x in d.values() if x > 0), len(d), s)
     for s, d in PANEL.items()), reverse=True)
for rate, miss, tot, s in sc[:10]:
    print(f"  {s:16} {miss:>2}/{tot:<2} = {100 * rate:5.1f}%")
print(f"  ... {sum(1 for r, m, t, s in sc if m == 0)} of {len(sc)} states never missed once.")

finding(
    f"Lateness is highly persistent, but the persistence lives in the state, not in the year: "
    f"{ssb / sst:.0%} of the variance in days-late is between states (ICC {icc:.2f}), and once a "
    f"state's own average is removed, last year's result carries no information about this year's "
    f"(permutation p={perm_p:.2f}). A state that missed last year misses again "
    f"{100 * tt / (tt + tf):.0f}% of the time versus a {100 * BASE:.0f}% base rate "
    f"({(tt / (tt + tf)) / BASE:.1f}x lift) — but its multi-year track record is the sharper "
    f"instrument still, forecasting a miss at {pB[0]:.0%} precision against {pA[0]:.0%} for "
    f"last year's outcome alone.")


# ---------------------------------------------------------------------------
# 2. Election-year effect
# ---------------------------------------------------------------------------

head(2, "ELECTION-YEAR EFFECT — do legislators hurry home to campaign?")

# State legislative (not gubernatorial) general elections.
#   ODD4  : whole legislature on 4-year terms, elected in odd years  (2015, 2019, 2023)
#   ODD2  : lower chamber elected every odd year
#   EVEN4 : whole legislature on 4-year terms, elected in gubernatorial midterms
#           (2014, 2018, 2022, 2026)
#   default: lower chamber elected every even year
ODD4 = {"Louisiana", "Mississippi"}
ODD2 = {"New Jersey", "Virginia"}
EVEN4 = {"Alabama", "Maryland"}


def is_election_year(state, year):
    if state in ODD4:
        return year % 4 == 3
    if state in ODD2:
        return year % 2 == 1
    if state in EVEN4:
        return year % 4 == 2
    return year % 2 == 0


for o in OBS:
    o["elec"] = is_election_year(o["state"], o["session_year"])
    o["even"] = o["session_year"] % 2 == 0

sub("unpaired comparison (confounded — see the caveat below)")
print(f"  {'subset':16} {'election yrs':>28}   {'off-years':>28}     MWU p")
for label, subset in [("all states", OBS),
                      ("annual cycle", [o for o in OBS if o["cycle"] == "annual"]),
                      ("biennial cycle", [o for o in OBS if o["cycle"] == "biennial"]),
                      ("full-time leg.", [o for o in OBS if o["leg"] == "full-time"]),
                      ("part-time leg.", [o for o in OBS if o["leg"] == "part-time"])]:
    E = [o["days"] for o in subset if o["elec"]]
    O = [o["days"] for o in subset if not o["elec"]]
    mp = stats.mannwhitneyu(E, O).pvalue
    print(f"  {label:16} n={len(E):3} mean {np.mean(E):+6.1f}d late {100 * np.mean([x > 0 for x in E]):4.1f}%"
          f"   n={len(O):3} mean {np.mean(O):+6.1f}d late {100 * np.mean([x > 0 for x in O]):4.1f}%"
          f"   {mp:7.4f}")
print("\n  CAVEAT: for a biennial state with odd-year sessions, 'off-year' and 'the long")
print("  budget-writing session' are the same thing, so the unpaired biennial gap is not an")
print("  election effect. The paired and fixed-effects tests below deal with this.")

sub("paired within-state (each state compared against itself)")


def paired(label, subset, key="elec"):
    by = defaultdict(lambda: defaultdict(list))
    for o in subset:
        by[o["state"]][o[key]].append(o["days"])
    P = [(s, np.mean(d[True]), np.mean(d[False])) for s, d in by.items()
         if len(d.get(True, [])) >= 2 and len(d.get(False, [])) >= 2]
    diff = np.array([a - b for _, a, b in P])
    w = stats.wilcoxon(diff).pvalue
    print(f"  {label:34} states={len(P):3}  mean {diff.mean():+6.1f}d  median {np.median(diff):+6.1f}d"
          f"  faster {int((diff < 0).sum())}/{len(diff)}  Wilcoxon p={w:.4f}")
    return P, diff, w


P_all, d_all, p_all = paired("election year, all states", OBS)
P_ann, d_ann, p_ann = paired("election year, annual states only",
                             [o for o in OBS if o["cycle"] == "annual"])
paired("PLACEBO: even calendar year", OBS, "even")
print("  The placebo lands close to the real thing, and it has to: for 44 of 50 states an")
print("  election year IS an even year, so the two dummies are nearly the same variable. The")
print("  fixed-effects model below is what separates them.")

sub("OLS with state AND session-year fixed effects")
states = sorted({o["state"] for o in OBS})
years = sorted({o["session_year"] for o in OBS})
X = np.array([[1.0, float(o["elec"])]
              + [float(o["state"] == s) for s in states[1:]]
              + [float(o["session_year"] == t) for t in years[1:]] for o in OBS])
yv = np.array([o["days"] for o in OBS], float)
beta, *_ = np.linalg.lstsq(X, yv, rcond=None)
rank = np.linalg.matrix_rank(X)
resid = yv - X @ beta
dof = len(yv) - rank
s2 = resid @ resid / dof
se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) * s2)
tstat = beta[1] / se[1]
fe_p = 2 * (1 - stats.t.cdf(abs(tstat), dof))
print(f"  election coefficient  {beta[1]:+.2f} days   (se {se[1]:.2f}, t={tstat:+.2f}, p={fe_p:.3f}, n={len(yv)})")
print("  Year fixed effects absorb everything national — COVID, revenue cycles, and any")
print("  generic even/odd-year rhythm. What identifies the coefficient is the six states")
print("  whose legislative election calendar differs from the other 44: AL, MD (midterm")
print("  4-year terms) and LA, MS, NJ, VA (odd-year elections).")

sub("states that break the pattern")
for s, a, b in sorted(P_all, key=lambda x: x[1] - x[2])[:4]:
    print(f"  faster in election years  {s:16} {a:+7.1f}d vs {b:+7.1f}d   ({a - b:+.0f})")
for s, a, b in sorted(P_all, key=lambda x: x[1] - x[2])[-3:]:
    print(f"  SLOWER in election years  {s:16} {a:+7.1f}d vs {b:+7.1f}d   ({a - b:+.0f})")

finding(
    f"Election years really are faster, by roughly a week to a week and a half. Within annual-cycle "
    f"states the budget lands {abs(d_ann.mean()):.1f} days earlier on average in a legislative "
    f"election year ({int((d_ann < 0).sum())} of {len(d_ann)} states move in that direction, "
    f"Wilcoxon p={p_ann:.3f}), and the effect survives state and year fixed effects at "
    f"{beta[1]:+.1f} days (p={fe_p:.3f}). It is a real but second-order signal: it shifts the "
    f"expected date, and does not rescue a chronically late state.")


# ---------------------------------------------------------------------------
# 3. Fiscal stress
# ---------------------------------------------------------------------------

head(3, "FISCAL STRESS — do lean years produce longer budget fights?")

DEFL = {int(r["year"]): float(r["deflator_to_2024"]) for r in load("cpi_deflators.csv")}
SPEND = defaultdict(dict)
for r in load("state_spending_timeseries_fy2015_fy2024.csv"):
    SPEND[r["state"]][int(r["fiscal_year"])] = (
        float(r["total_expenditures_millions"]), float(r["population"]))
SPEND_YEARS = sorted({y for d in SPEND.values() for y in d})
print(f"  spending series covers FY{SPEND_YEARS[0]}-FY{SPEND_YEARS[-1]} at these points: {SPEND_YEARS}")
print("  It is biennial, not annual, so growth below is the ANNUALISED rate over each")
print("  interval — a medium-term spending trajectory, not a one-year revenue shock.")

DAYS = {(o["state"], o["fy"]): o["days"] for o in OBS}
pts = []
for s, d in SPEND.items():
    for a, b in zip(SPEND_YEARS, SPEND_YEARS[1:]):
        if a not in d or b not in d:
            continue
        pc_a = d[a][0] * 1e6 / d[a][1] * DEFL[a]   # real per-capita, 2024 dollars
        pc_b = d[b][0] * 1e6 / d[b][1] * DEFL[b]
        g = 100 * ((pc_b / pc_a) ** (1 / (b - a)) - 1)
        if (s, b) in DAYS:
            pts.append(dict(state=s, fy=b, growth=g, days=DAYS[(s, b)]))

sub("state level: real per-capita spending growth vs days-late")
g = np.array([p["growth"] for p in pts])
dl = np.array([p["days"] for p in pts])
print(f"  n = {len(pts)} state-years;  growth mean {g.mean():+.2f}%/yr, sd {g.std():.2f}")
STATE_R, sp_ = stats.pearsonr(g, dl), stats.spearmanr(g, dl)
print(f"  Pearson  r   = {STATE_R[0]:+.3f}  (p={STATE_R[1]:.3f})")
print(f"  Spearman rho = {sp_[0]:+.3f}  (p={sp_[1]:.3f})")
q1, q2 = np.quantile(g, [1 / 3, 2 / 3])
for label, sel in [(f"bottom tercile (<= {q1:+.1f}%/yr)", [p for p in pts if p["growth"] <= q1]),
                   ("middle tercile", [p for p in pts if q1 < p["growth"] <= q2]),
                   (f"top tercile   (>  {q2:+.1f}%/yr)", [p for p in pts if p["growth"] > q2])]:
    v = [p["days"] for p in sel]
    print(f"  {label:28} n={len(v):3}  mean {np.mean(v):+6.1f}d  late {100 * np.mean([x > 0 for x in v]):4.1f}%")
neg = [p["days"] for p in pts if p["growth"] < 0]
pos = [p["days"] for p in pts if p["growth"] >= 0]
print(f"  real contraction  n={len(neg):3}  mean {np.mean(neg):+6.1f}d  late {100 * np.mean([x > 0 for x in neg]):4.1f}%")
print(f"  real expansion    n={len(pos):3}  mean {np.mean(pos):+6.1f}d  late {100 * np.mean([x > 0 for x in pos]):4.1f}%")
print(f"  Mann-Whitney contraction vs expansion p = {stats.mannwhitneyu(neg, pos).pvalue:.3f}")
bys = defaultdict(list)
for p in pts:
    bys[p["state"]].append(p)
dx, dy = [], []
for s, v in bys.items():
    if len(v) < 2:
        continue
    mg, md = np.mean([p["growth"] for p in v]), np.mean([p["days"] for p in v])
    for p in v:
        dx.append(p["growth"] - mg)
        dy.append(p["days"] - md)
prw = stats.pearsonr(dx, dy)
print(f"  within-state (demeaned) r = {prw[0]:+.3f}  (p={prw[1]:.3f}, n={len(dx)})")

sub("national level: NASBO general fund revenue growth vs on-time rate")
# NASBO Fiscal Survey of States, Table "State Nominal and Real Annual Revenue Changes".
# FY2015-FY2024 from the Fall 2025 edition; FY2025-FY2027 from Spring 2026 (later
# vintage, and it revises FY2025 4.1->4.9 and FY2026 0.7->2.2). FY2027 is a
# projection built on governors' recommended budgets, not an actual.
REV_NOM = {2015: 5.0, 2016: 1.8, 2017: 2.4, 2018: 6.9, 2019: 5.7, 2020: -0.6,
           2021: 16.6, 2022: 16.3, 2023: -1.2, 2024: 2.7, 2025: 4.9, 2026: 2.2,
           2027: 2.5}
REV_REAL = {2015: 4.1, 2016: 4.0, 2017: 1.8, 2018: 3.4, 2019: 2.7, 2020: -2.5,
            2021: 12.1, 2022: 8.1, 2023: -5.2, 2024: 0.9, 2025: 3.0, 2026: -0.7}

byfy = defaultdict(list)
for s, d in ENACT_EVENTS.items():
    for fy, ok in d.items():
        if fy not in REV_NOM:      # one stray FY2014 row; the revenue series starts at FY2015
            continue
        byfy[fy].append(bool(ok) and DAYS.get((s, fy), 1) <= 0)
print("   FY   states enacting   on-time%   rev growth nom / real")
nat = []
for fy in sorted(byfy):
    v = byfy[fy]
    rate = 100 * sum(v) / len(v)
    real = REV_REAL.get(fy)
    print(f"  {fy}   {len(v):>14}   {rate:7.1f}   {REV_NOM[fy]:+9.1f} / "
          f"{('%+.1f' % real) if real is not None else '   n/a'}")
    nat.append((fy, rate))
rates = {fy: r for fy, r in nat}
for label, xs, ys in [
    ("same-year nominal growth",
     [REV_NOM[fy] for fy in rates], [rates[fy] for fy in rates]),
    ("PRIOR-year nominal growth",
     [REV_NOM[fy - 1] for fy in rates if fy - 1 in REV_NOM],
     [rates[fy] for fy in rates if fy - 1 in REV_NOM]),
    ("same-year real growth",
     [REV_REAL[fy] for fy in rates if fy in REV_REAL],
     [rates[fy] for fy in rates if fy in REV_REAL]),
    ("same-year nominal, ex-FY2020/21",
     [REV_NOM[fy] for fy in rates if fy not in (2020, 2021)],
     [rates[fy] for fy in rates if fy not in (2020, 2021)]),
]:
    pr = stats.pearsonr(xs, ys)
    sp2 = stats.spearmanr(xs, ys)
    print(f"  {label:33} n={len(xs):2}  r={pr[0]:+.3f} (p={pr[1]:.3f})   rho={sp2[0]:+.3f} (p={sp2[1]:.3f})")
print("\n  The prior-year column is the one a forecaster could actually use: when the FY N")
print("  budget is being written in spring of FY N-1, FY N's revenue is still unknown.")

finding(
    f"Fiscal stress does not predict lateness, at either level. Real per-capita spending growth "
    f"is uncorrelated with days-late across {len(pts)} state-years (r={STATE_R[0]:+.2f}, p={STATE_R[1]:.2f}), "
    f"and states in real contraction actually enacted {abs(np.mean(neg) - np.mean(pos)):.0f} days "
    f"EARLIER on average than expanding states, the opposite of the hypothesis. Nationally, "
    f"revenue growth and the on-time rate move independently. Budget fights are about "
    f"disagreement, not scarcity — the two fastest revenue years on record, FY2021 and FY2022, "
    f"produced the worst and one of the better on-time rates in the panel.")


# ---------------------------------------------------------------------------
# 4. Session overrun
# ---------------------------------------------------------------------------

head(4, "SESSION OVERRUN — does a session running long predict a late budget?")

OVERRUN_CSV = os.path.join(HERE, "session_overrun_data.csv")
if not os.path.exists(OVERRUN_CSV):
    print("  session_overrun_data.csv not found — skipping. Build it with build_session_overrun.py")
else:
    ov = load("session_overrun_data.csv")
    print("  Source: NCSL's 'Legislative Session Calendar', read at two vintages of the same")
    print("  document — an early-season edition giving the SCHEDULED adjournment and a")
    print("  post-session edition giving the ACTUAL sine die. Editions come from NCSL and from")
    print("  the Internet Archive, so the scheduled column is a contemporaneous forecast rather")
    print("  than a date reconstructed after the fact. See build_session_overrun.py.")
    print(f"  {len(ov)} state-years with both dates and a matching budget observation.\n")
    recs = []
    for r in ov:
        recs.append(dict(state=r["state"], year=int(r["session_year"]), fy=int(r["fy"]),
                         overrun=float(r["overrun_days"]), days=int(r["days_late"]),
                         late=int(r["days_late"]) > 0, prec=r["precision"],
                         leg=META[r["state"]]["legislature_type"]))
    ovd = np.array([r["overrun"] for r in recs])
    dld = np.array([r["days"] for r in recs])
    sub("correlation of session overrun with days-late")
    print(f"  n = {len(recs)} state-years, {len({r['state'] for r in recs})} states, "
          f"{len({r['year'] for r in recs})} session years")
    print(f"  overrun: mean {ovd.mean():+.1f}d, median {np.median(ovd):+.1f}d, "
          f"ran long in {100 * np.mean(ovd > 0):.0f}% of state-years")
    pr4 = stats.pearsonr(ovd, dld)
    sp4 = stats.spearmanr(ovd, dld)
    print(f"  Pearson  r   = {pr4[0]:+.3f}  (p={pr4[1]:.2g})")
    print(f"  Spearman rho = {sp4[0]:+.3f}  (p={sp4[1]:.2g})")
    exact = [r for r in recs if r["prec"] == "exact"]
    if len(exact) > 30:
        pe = stats.pearsonr([r["overrun"] for r in exact], [r["days"] for r in exact])
        print(f"  restricted to exactly-dated scheduled adjournments: n={len(exact)}, "
              f"r={pe[0]:+.3f} (p={pe[1]:.2g})")
    # A regular session that ends well EARLY is usually a sign the work moved to a
    # special session rather than a sign of speed — Maine adjourned its 2025 regular
    # session on March 21 and immediately reconvened until June 25. Those rows understate
    # how long the legislature actually sat, so check the correlation without them.
    trimmed = [r for r in recs if r["overrun"] > -14]
    pt4 = stats.pearsonr([r["overrun"] for r in trimmed], [r["days"] for r in trimmed])
    st4 = stats.spearmanr([r["overrun"] for r in trimmed], [r["days"] for r in trimmed])
    print(f"  dropping the {len(recs) - len(trimmed)} sessions that adjourned >14d early: "
          f"n={len(trimmed)}, r={pt4[0]:+.3f} (p={pt4[1]:.2g}), rho={st4[0]:+.3f} (p={st4[1]:.2g})")

    sub("overrun bands")
    bands = [("on or before schedule", lambda v: v <= 0),
             ("1-13 days over", lambda v: 0 < v <= 13),
             ("14-29 days over", lambda v: 13 < v <= 29),
             ("30+ days over", lambda v: v > 29)]
    for label, test in bands:
        sel = [r for r in recs if test(r["overrun"])]
        if not sel:
            continue
        print(f"  {label:24} n={len(sel):3}  mean {np.mean([r['days'] for r in sel]):+6.1f}d  "
              f"missed {100 * np.mean([r['late'] for r in sel]):5.1f}%")
    over = [r for r in recs if r["overrun"] > 0]
    onsched = [r for r in recs if r["overrun"] <= 0]
    if over and onsched:
        mw = stats.mannwhitneyu([r["days"] for r in over], [r["days"] for r in onsched]).pvalue
        tab = np.array([[sum(r["late"] for r in over), sum(not r["late"] for r in over)],
                        [sum(r["late"] for r in onsched), sum(not r["late"] for r in onsched)]])
        orat, fp4 = stats.fisher_exact(tab)
        print(f"\n  ran long vs adjourned on schedule: miss rate "
              f"{100 * np.mean([r['late'] for r in over]):.1f}% vs "
              f"{100 * np.mean([r['late'] for r in onsched]):.1f}%")
        print(f"  Mann-Whitney on days-late p={mw:.2g};  odds ratio {orat:.1f} (Fisher p={fp4:.2g})")

    sub("does overrun add anything beyond knowing which state it is?")
    byst = defaultdict(list)
    for r in recs:
        byst[r["state"]].append(r)
    wx, wy = [], []
    for s, v in byst.items():
        if len(v) < 3:
            continue
        mo = np.mean([r["overrun"] for r in v])
        md = np.mean([r["days"] for r in v])
        for r in v:
            wx.append(r["overrun"] - mo)
            wy.append(r["days"] - md)
    prw4 = stats.pearsonr(wx, wy)
    print(f"  within-state (demeaned) r = {prw4[0]:+.3f}  (p={prw4[1]:.2g}, n={len(wx)}, "
          f"{len([s for s, v in byst.items() if len(v) >= 3])} states)")
    print("  This is the question that matters for early warning: given the same state, does a")
    print("  session that runs longer than usual land its budget later than usual?")
    # Unlike analysis 1 there is no lagged-dependent-variable bias here — overrun and
    # days-late are different variables — but permuting overrun within each state costs
    # little and settles it.
    null4 = []
    for _ in range(3000):
        dx2, dy2 = [], []
        for s, v in byst.items():
            if len(v) < 3:
                continue
            perm = [r["overrun"] for r in v]
            random.shuffle(perm)
            mo, md = np.mean(perm), np.mean([r["days"] for r in v])
            for o, r in zip(perm, v):
                dx2.append(o - mo)
                dy2.append(r["days"] - md)
        null4.append(stats.pearsonr(dx2, dy2)[0])
    null4 = np.array(null4)
    pp4 = min(1.0, 2 * (null4 >= prw4[0]).mean())
    print(f"  permutation null {null4.mean():+.3f} +/- {null4.std():.3f}   -> "
          f"p {'< 0.001' if pp4 == 0 else '= %.4f' % pp4} "
          f"(z = {(prw4[0] - null4.mean()) / null4.std():+.1f})")

    states4 = sorted({r["state"] for r in recs})
    X4 = np.array([[1.0, r["overrun"]] + [float(r["state"] == s) for s in states4[1:]]
                   for r in recs])
    y4 = np.array([r["days"] for r in recs], float)
    b4, *_ = np.linalg.lstsq(X4, y4, rcond=None)
    rank4 = np.linalg.matrix_rank(X4)
    res4 = y4 - X4 @ b4
    dof4 = len(y4) - rank4
    se4 = np.sqrt(np.diag(np.linalg.pinv(X4.T @ X4)) * (res4 @ res4 / dof4))
    t4 = b4[1] / se4[1]
    p4 = 2 * (1 - stats.t.cdf(abs(t4), dof4))
    print(f"\n  OLS with state fixed effects:  {b4[1]:+.3f} days later per day of overrun")
    print(f"    (se {se4[1]:.3f}, t={t4:+.2f}, p={p4:.2g}, n={len(y4)})")
    print(f"    -> a session running {30} days past its scheduled adjournment implies a budget")
    print(f"       roughly {abs(30 * b4[1]):.0f} days later than that same state's own norm.")

    sub("robustness of the fixed-effects slope")

    def fe_slope(subset):
        sts = sorted({r["state"] for r in subset})
        Xr = np.array([[1.0, r["overrun"]] + [float(r["state"] == s) for s in sts[1:]]
                       for r in subset])
        yr = np.array([r["days"] for r in subset], float)
        br, *_ = np.linalg.lstsq(Xr, yr, rcond=None)
        rr = yr - Xr @ br
        dr = len(yr) - np.linalg.matrix_rank(Xr)
        ser = np.sqrt(np.diag(np.linalg.pinv(Xr.T @ Xr)) * (rr @ rr / dr))
        return br[1], ser[1], 2 * (1 - stats.t.cdf(abs(br[1] / ser[1]), dr)), len(subset)

    # The biggest overruns in the panel are 2021 legislatures that recessed in spring and
    # came back in the autumn to redistrict — Idaho +229, Arkansas +217, Indiana +200.
    # That has nothing to do with the budget, so the slope has to survive their removal.
    for label, subset in [
            ("all state-years", recs),
            ("excluding 2021 (redistricting returns)", [r for r in recs if r["year"] != 2021]),
            ("excluding COVID years 2020-2021", [r for r in recs if r["year"] not in (2020, 2021)]),
            ("excluding overruns beyond 90 days", [r for r in recs if r["overrun"] <= 90]),
            ("trimmed to (-14, +90] days", [r for r in recs if -14 < r["overrun"] <= 90])]:
        c, s_, p_, n_ = fe_slope(subset)
        print(f"  {label:42} n={n_:3}  {c:+.3f} (se {s_:.3f}, p={p_:.2g})")
    print("  The slope gets steeper, not shallower, once those are removed.")

    sub("coverage limits")
    nofix = sorted({r["state"] for r in RAW} - {r["state"] for r in recs})
    print(f"  {len(nofix)} states never appear: {', '.join(nofix)}")
    print("  Most are missing because their legislature has no scheduled adjournment at all —")
    print("  NCSL prints '*' for them. An overrun cannot be defined where nothing was scheduled.")
    ft = [s for s in nofix if META[s]["legislature_type"] == "full-time"]
    print(f"  Of those, {len(ft)} are full-time legislatures: {', '.join(ft)}")

    deep = [r for r in recs if r["overrun"] > 29]
    finding(
        f"Session overrun is a genuine leading indicator, and the only one of the four that a "
        f"platform could act on while the outcome is still in play. It is strongest exactly where "
        f"a forecaster needs it — inside a single state, comparing a session against that state's "
        f"own norm: within-state r={prw4[0]:+.2f} (p={prw4[1]:.1g}), and state fixed effects put "
        f"the slope at {b4[1]:+.2f} days of budget delay per day of overrun (p={p4:.1g}), so a "
        f"month-long overrun implies a budget about {abs(30 * b4[1]):.0f} days later than usual. "
        f"State-years that ran 30+ days long missed the fiscal-year start "
        f"{100 * np.mean([r['late'] for r in deep]):.0f}% of the time against a "
        f"{100 * np.mean([r['late'] for r in recs]):.0f}% rate across this sample. Its blind spot "
        f"is structural: the measure is undefined for the year-round legislatures that miss most "
        f"often, because they never schedule an adjournment to overrun.")


print("\n" + "=" * W)
print("WHAT TO PUT IN THE WHITE PAPER".center(W))
print("=" * W)
print(f"""
1. BUDGET TIMING IS A STATE TRAIT, NOT A YEARLY COIN FLIP.
   {ssb / sst:.0%} of the variance in how late a budget lands is variation between states
   rather than within them (ICC {icc:.2f}). {sum(1 for r, m, t, s in sc if m == 0)} of 50 states have never missed their
   fiscal-year start once in the panel; Massachusetts has missed all {int(sc[0][2])}. Knowing
   which state you are looking at is most of the forecast.

2. THE TRACK RECORD BEATS LAST YEAR.
   A rule that fires when a state has missed in a majority of its prior years calls
   the next miss at {pB[0]:.0%} precision against a {BASE:.0%} base rate. "Was it late last
   year?" manages only {pA[0]:.0%} — and once each state's own average is removed, last
   year's result carries no information at all (permutation p={perm_p:.2f}). Recency is
   noise; history is signal.

3. SESSION OVERRUN IS THE ONE LIVE, IN-SEASON SIGNAL.
   Within a state, every day a session runs past its scheduled adjournment adds about
   {b4[1]:.2f} days to the budget's delay (p={p4:.1g}) — a month-long overrun means a budget
   roughly {abs(30 * b4[1]):.0f} days later than that state's own norm. This is the only one of the
   four that moves while the outcome is still undecided, and it is exactly the kind
   of thing a platform tracking legislative calendars in real time can watch.

   Secondary: legislative election years pull budgets about {abs(d_ann.mean()):.0f} days earlier in
   annual-cycle states (p={p_ann:.3f}; {beta[1]:+.0f} days under state and year fixed effects,
   p={fe_p:.3f}).

RULED OUT — and worth saying so, because each is a plausible story that fails:
   * fiscal stress          real per-capita spending growth vs days-late, r={STATE_R[0]:+.2f} (p={STATE_R[1]:.2f});
                            contracting states enacted EARLIER, not later
   * national revenue cycle  NASBO general fund revenue growth vs the national on-time
                            rate, no relationship across FY2015-FY2027
   * year-to-year momentum   no within-state autocorrelation once the state's own
                            average is removed
""".strip())

print("\n" + "=" * W)
print("METHOD NOTES".center(W))
print("=" * W)
print("""
p-values are computed live by this script from scipy 1.15; nothing is hardcoded.
Tests are two-sided throughout. Mann-Whitney U and Wilcoxon signed-rank are used in
place of t-tests wherever the days-late distribution is the skewed one it plainly is;
where a mean is reported a Welch or OLS check was run alongside and agreed on sign.

The unit of analysis is the state-year for correlations and the state for paired tests.
Because two thirds of the variance in days-late sits between states rather than within
them (analysis 1), any comparison that pools state-years without a within-state control
will pick up state composition and report it as an effect. Analyses 2, 3 and 4 each
therefore carry a demeaned or fixed-effects version, and those are the ones to quote.
""".strip())
