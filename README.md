# State Budget Timing — All 50 States

How late (or early) does each state enact its budget relative to its own fiscal year
start? 651 state-fiscal-years, FY2015–FY2027, verified against primary sources, plus a
forward-looking risk model for FY2028.

**Live:** <https://hotdogvulkin.github.io/Roboro-Capstone/>

## What's here

```
index.html      the dashboard — standalone, no build step, no network dependencies
og-card.png     link preview image
data/           the datasets the dashboard is built from
analysis/       the statistics, and the scripts that produced the data
```

`index.html` is fully self-contained: Chart.js and the Inter typeface are embedded
rather than loaded from a CDN, so it renders identically offline, on a locked-down
conference network, or straight off the filesystem. Open it by double-clicking — no
server required.

## The dashboard

Five views:

| | |
|---|---|
| **Snapshot** | All 50 states by average days past fiscal year start. The landing view. |
| **Trend** | Per-state heatmap, FY2014–FY2027, plus the national on-time rate. |
| **Watchlist** | FY2028 late-risk, scored and ranked. |
| **Sessions** | How far each legislature ran past its own scheduled adjournment. |
| **Findings** | What predicts a late budget, and what turns out not to. |

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

**Ruled out**, each a plausible story the data does not support: budget cycle
(annual vs. biennial), state size, spending level, party control on its own, fiscal
stress, the national revenue cycle, and year-to-year momentum.

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

Prints the full report — four analyses, test statistics, robustness cuts and method
notes. `budget_timing_predictive_findings.txt` is the saved output of that run.

`build_session_overrun.py` rebuilds the session dataset from NCSL calendar PDFs;
`ncsl_parse.py` is the table parser it uses.

## Deploying

It is one static file. On GitHub Pages, push this folder and enable Pages on the branch
— no build, no configuration. `index.html` at the repo root is served automatically.

---

Capstone prototype · Summer 2026 · Grant Garcia
