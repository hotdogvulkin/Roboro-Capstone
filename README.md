# State Budget Timing — All 50 States

How late (or early) does each state enact its budget relative to its own fiscal year
start? 651 state-fiscal-years, FY2015–FY2027, verified against primary sources, plus a
forward-looking risk model for FY2028.

**Live:** <https://hotdogvulkin.github.io/Roboro-Capstone/>

## What's here

```
src/dashboard.html   the source — this is the only file you edit
src/vendor/          Chart.js and Inter, vendored so builds are reproducible
src/og-card.svg      source of the link-preview image
build.py             src/ -> index.html
index.html           GENERATED. Overwritten on every build; do not edit
og-card.png          generated link preview
data/                the datasets the dashboard is built from
analysis/            the statistics, and the scripts that produced the data
```

GitHub Pages serves the repo root, which is why the built page has to land there as
`index.html` rather than in a `dist/` directory. It carries a "generated file" banner
so nobody edits it by mistake.

## Building

```bash
python3 build.py           # rebuild index.html from src/
python3 build.py --check   # verify index.html matches src/ (exit 1 if stale)
```

No dependencies — standard library only. The build inlines Chart.js and the Inter
typeface from `src/vendor/`, so the published page makes **no network requests at all**
and renders identically offline, on a locked-down conference network, or opened
straight off the filesystem. Both are checked into the repo rather than downloaded at
build time, so a build does not depend on cdnjs or Google Fonts being reachable.

It also adds the description, favicon and Open Graph tags that make a shared link
render as a preview card. `BASE_URL` at the top of `build.py` is the only thing to
change if the site ever moves.

Run `--check` before pushing. If it fails, you edited `index.html` instead of
`src/dashboard.html`, or forgot to rebuild.

## The dashboard

Six views:

| | |
|---|---|
| **Snapshot** | All 50 states by average days past fiscal year start. The landing view. |
| **Trend** | Per-state heatmap, FY2014–FY2027, plus the national on-time rate. |
| **Watchlist** | FY2028 late-risk, scored and ranked. |
| **Sessions** | How far each legislature ran past its own scheduled adjournment. |
| **Findings** | What predicts a late budget, and what turns out not to. |
| **Open questions** | What the data raises and cannot settle, and the gaps we'd like help closing. |

Every descriptive figure is computed from the dataset at render time rather than typed
in, so the panels cannot drift from each other or from the data. The only hardcoded
values are p-values, which are run offline in scipy and labelled as such.

## Findings

**Budget timing is a state trait, not a yearly coin flip.** 65% of the variance in how
late a budget lands is variation *between* states rather than within them (ICC 0.62).
28 of 50 states have never missed a deadline on record. Massachusetts has missed all 13.

**The track record beats last year.** A state that has missed in a majority of its prior
years misses again at 82% precision against a 15% base rate — a 5.3× lift, scored
walk-forward using only earlier data. "Was it late last year?" manages 59%, and once
each state's own average is removed, last year carries no information at all (p = 0.43).

**Session overrun is the one live signal.** Within a state, each day a session runs past
its scheduled adjournment adds ~0.25 days of budget delay (p = 2e-06). It is the only
measure here that moves while the outcome is still undecided — and its blind spot is
structural: the year-round legislatures that miss most often never schedule an
adjournment to overrun.

**Party is the seductive null.** Republican-trifecta states miss 4.7% of budgets against
22.4% for Democratic ones (p = 0.002) — but 62.5% of Democratic-trifecta states have
full-time legislatures against 8.7% of Republican ones. Put both in one model and
legislature type is worth +27 points (p = 0.001) while party is worth nothing (p = 0.74).
It was professionalism wearing a party label.

**Ruled out**, each a plausible story the data does not support: budget cycle
(annual vs. biennial), state size, spending level, party control, party direction, fiscal
stress, the national revenue cycle, year-to-year momentum, and budgets getting later over
time (+0.05 d/yr, p = 0.90 — and national spending is flat per person in real terms).

## Data

`data/budget_timing_pilot_data_cleaned.csv` — one row per state per fiscal year:
signing date, days late, whether a budget was enacted at all, date precision, and a
source and note for every row.

Of 651 rows: 575 carry an exact signing date, 67 are dated to the month where no source
gives the day, and 9 record a fiscal year that ended with no budget enacted. Biennial
carryovers are marked and excluded from every statistic — they duplicate their parent
year's date and would manufacture correlation.

`data/session_overrun_data.csv` — 410 sessions across 44 states, scheduled vs. actual
adjournment, built from two vintages of NCSL's Legislative Session Calendar per year so
the scheduled column is a contemporaneous forecast rather than a date reconstructed
afterwards.

Sources: NASBO *Summaries of Proposed & Enacted Budgets* and *Fiscal Survey of States*;
state session laws and governors' offices; NCSL *Legislative Session Calendar*; BLS
CPI-U; Census / Tax Policy Center.

## Reproducing the analysis

```bash
cd analysis
pip install numpy scipy
python3 budget_timing_predictive_analysis.py
```

Prints the full report — seven analyses, test statistics, robustness cuts and method
notes, and reproduces **every** figure cited on the dashboard.
`budget_timing_predictive_findings.txt` is the saved output of that run.

`build_session_overrun.py` rebuilds the session dataset from NCSL calendar PDFs;
`ncsl_parse.py` is the table parser it uses.

## Deploying

```bash
python3 build.py && git add -A && git commit -m "..." && git push
```

Pages is configured to serve `main` at the repo root and rebuilds on push, usually
within a minute.

---

Capstone prototype · Summer 2026 · Grant Garcia
