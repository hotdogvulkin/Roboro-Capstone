#!/usr/bin/env python3
"""
Build session_overrun_data.csv — scheduled vs actual legislative adjournment
============================================================================

The idea: NCSL republishes its "Legislative Session Calendar" many times over the
course of a year, and every edition carries its own date in the header. An edition
printed before the sessions end shows the adjournment each legislature has
SCHEDULED; an edition printed after they go home shows when each one ACTUALLY
adjourned sine die. Diff two editions of the same year and you get the overrun.

Every edition used here is either live from NCSL or pulled from the Internet
Archive, so the "scheduled" column is a genuine contemporaneous forecast and not a
date reconstructed after the fact.

Two guards, applied per state rather than per year, keep the comparison honest:

  * the SCHEDULED date only counts if the edition it came from was published on or
    before that date — otherwise the "schedule" may already be a report of what
    happened, and the overrun would collapse to a spurious zero; and
  * the ACTUAL date only counts if its edition was published on or after that date
    — otherwise the sitting had not finished and NCSL is still printing the plan.

States NCSL marks "*" — no fixed adjournment — are dropped throughout. An overrun
cannot be defined against a schedule that does not exist.

Usage:
    python3 build_session_overrun.py <dir-of-ncsl-session-calendar-pdfs>
"""

import csv
import os
import re
import sys
from datetime import date

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ncsl_parse import parse_pdf, parse_date  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}


def identify(path):
    """(session_year, edition_date) read out of the PDF's own first page."""
    try:
        text = pymupdf.open(path)[0].get_text()
    except Exception:
        return None
    my = re.search(r"(20\d\d)\s+LEGISLATIVE SESSION CALENDAR", text)
    ed = re.search(r"\((?:Updated\s+)?([A-Z][a-z]+)\.?\s+(\d{1,2}),?\s*(20\d\d)\)", text)
    if not my or not ed or ed.group(1) not in MONTHS:
        return None
    return int(my.group(1)), date(int(ed.group(3)), MONTHS[ed.group(1)], int(ed.group(2)))


def main(pdf_dir):
    editions = {}
    for fn in sorted(os.listdir(pdf_dir)):
        if not fn.lower().endswith(".pdf"):
            continue
        got = identify(os.path.join(pdf_dir, fn))
        if got:
            editions.setdefault(got[0], {})[got[1]] = os.path.join(pdf_dir, fn)

    rows, provenance = [], []
    for year in sorted(editions):
        vints = sorted(editions[year])
        if len(vints) < 2:
            print(f"  {year}: only one edition ({vints[0]}) — skipped")
            continue
        parsed = {v: parse_pdf(editions[year][v]) for v in vints}

        def dated(v, st):
            """Parsed adjournment for one state in one edition, or (None, reason).

            Anything outside the session year's own calendar window is rejected. NCSL
            occasionally prints the end of a two-year legislative assembly instead of
            the year's sine die — the November 2022 sheet gives Delaware's 2023
            adjournment as "Jan. 9, 2024" — and that is a different quantity.
            """
            iso, prec = parse_date(parsed[v].get(st, ("", "", ""))[1], year)
            if not iso:
                return None, None
            d = date.fromisoformat(iso)
            if not (date(year - 1, 12, 1) <= d <= date(year, 12, 31)):
                return None, None
            return d, prec
        kept = nofix = unmatched = 0
        used_sched, used_act = set(), set()
        for st in sorted({s for tbl in parsed.values() for s in tbl}):
            # SCHEDULED: walk forward from the oldest edition and take the first one
            # whose own publication date still precedes the adjournment it prints.
            sched = next(((v, *dated(v, st)) for v in vints
                          if dated(v, st)[0] and v <= dated(v, st)[0]), None)
            # ACTUAL: walk backward from the newest and take the first edition that both
            # still lists the state and was published on or after the date it prints.
            # Walking backward matters: NCSL blanks out old rows in much later reissues,
            # so the very newest edition of an old year is often the emptiest.
            act = next(((v, *dated(v, st)) for v in reversed(vints)
                        if dated(v, st)[0] and v >= dated(v, st)[0]), None)
            if sched is None and act is None:
                nofix += 1
                continue
            if sched is None or act is None or sched[0] == act[0]:
                unmatched += 1
                continue
            sd_d, ad_d = sched[1], act[1]
            rows.append(dict(state=st, session_year=year,
                             scheduled_adjourn=sd_d.isoformat(),
                             actual_adjourn=ad_d.isoformat(),
                             overrun_days=(ad_d - sd_d).days,
                             precision="exact" if sched[2] == "exact" and act[2] == "exact"
                                       else "approx",
                             scheduled_edition=sched[0].isoformat(),
                             actual_edition=act[0].isoformat()))
            used_sched.add(sched[0])
            used_act.add(act[0])
            kept += 1
        print(f"  {year}: {len(vints)} editions {vints[0]}..{vints[-1]} -> {kept} states "
              f"({nofix} with no fixed adjournment, {unmatched} without a usable pair)")
        provenance.append((year, ";".join(sorted(v.isoformat() for v in used_sched)),
                           ";".join(sorted(v.isoformat() for v in used_act)), kept,
                           len(vints), f"{vints[0]}..{vints[-1]}"))

    # ---- join to the budget timing panel on (state, session year)
    budget = {}
    with open(os.path.join(HERE, "budget_timing_pilot_data_cleaned.csv")) as fh:
        for r in csv.DictReader(fh):
            if r["enactment_type"] == "biennial carryover":
                continue
            if r["budget_enacted"] != "yes" or not r["days_late"]:
                continue
            budget[(r["state"], int(r["fy_start_date"][:4]))] = (
                int(r["fy_label"][2:]), int(r["days_late"]), r["signed_date"])

    out = []
    for r in rows:
        key = (r["state"], r["session_year"])
        if key not in budget:
            continue
        fy, days, signed = budget[key]
        out.append(dict(r, fy=fy, signed_date=signed, days_late=days,
                        source="NCSL Legislative Session Calendar, early vs post-session "
                               "edition of the same year"))

    cols = ["state", "session_year", "fy", "scheduled_adjourn", "actual_adjourn",
            "overrun_days", "precision", "signed_date", "days_late",
            "scheduled_edition", "actual_edition", "source"]
    path = os.path.join(HERE, "session_overrun_data.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows({c: r[c] for c in cols} for r in sorted(
            out, key=lambda r: (r["state"], r["session_year"])))
    print(f"\nwrote {path}: {len(out)} state-years, {len({r['state'] for r in out})} states, "
          f"{len({r['session_year'] for r in out})} session years")

    ppath = os.path.join(HERE, "session_overrun_sources.csv")
    with open(ppath, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["session_year", "scheduled_editions_used", "actual_editions_used",
                    "states_kept", "editions_available", "edition_date_range"])
        w.writerows(provenance)
    print(f"wrote {ppath}: which edition of the calendar each year was read from")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
