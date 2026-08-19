const fs = require('fs');
const {Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, ImageRun,
       BorderStyle, PageOrientation, convertInchesToTwip} = require('docx');

const P = '/Users/grantgarcia/Desktop/Roboro-Capstone/paper/';
const INK='1A1626', MUTED='6B6480', PINK='E60058', RULE='E3E0EA';

const t = (text,o={}) => new TextRun({text, font:'Calibri', size:o.size||22,
  bold:o.bold||false, italics:o.i||false, color:o.color||INK});
const para = (runs,o={}) => new Paragraph({children:Array.isArray(runs)?runs:[runs],
  spacing:{after:o.after===undefined?160:o.after, before:o.before||0, line:276},
  alignment:o.align||AlignmentType.LEFT, ...(o.border?{border:o.border}:{})});
const body = (s,o={}) => para(t(s,o),o);
const h1 = s => new Paragraph({children:[t(s,{size:30,bold:true})],
  spacing:{before:340,after:150}, heading:HeadingLevel.HEADING_1});
const h2 = s => new Paragraph({children:[t(s,{size:24,bold:true})],
  spacing:{before:240,after:110}, heading:HeadingLevel.HEADING_2});
const bullet = s => new Paragraph({children:[t(s)], bullet:{level:0},
  spacing:{after:90, line:276}});
const rule = () => new Paragraph({children:[t('')], spacing:{after:120},
  border:{bottom:{style:BorderStyle.SINGLE,size:6,color:RULE}}});

function figure(file,w,h,caption){
  const data = fs.readFileSync(P+file);
  const W = 620, H = Math.round(620*h/w);
  return [
    new Paragraph({children:[new ImageRun({data, type:'png',
      transformation:{width:W, height:H}})],
      spacing:{before:200, after:60}, alignment:AlignmentType.CENTER}),
    new Paragraph({children:[t(caption,{size:17,color:MUTED,i:true})],
      spacing:{after:240}, alignment:AlignmentType.CENTER})
  ];
}

const stat = (v,label) => new Paragraph({children:[
  t(v+'  ',{size:32,bold:true,color:PINK}), t(label,{size:19,color:MUTED})],
  spacing:{after:70}});

const doc = new Document({
  creator:'Grant Garcia', title:'Predictably Late',
  description:'A 50-state analysis of budget timing and predictive signals',
  sections:[{
    properties:{page:{size:{width:12240,height:15840},
      margin:{top:1100,right:1100,bottom:1100,left:1100}}},
    children:[
    // ---- cover ----
    para(t('ROBORO',{size:20,bold:true,color:PINK}),{after:0}),
    para(t('Legislative Intelligence',{size:19,color:MUTED}),{after:340}),
    new Paragraph({children:[t('Predictably Late',{size:52,bold:true})],spacing:{after:80}}),
    new Paragraph({children:[t('Why a handful of states miss every year — and how to see it coming',
      {size:26,color:MUTED})],spacing:{after:260}}),
    body('A 50-state analysis of budget timing, spending, and predictive signals.',{size:21}),
    body('Based on 651 verified state-fiscal-years, FY2014–FY2027.',{size:21,color:MUTED,after:300}),
    body('Grant Garcia  ·  Summer 2026 Research Fellow  ·  Roboro AI',{size:20,color:MUTED,after:40}),
    body('hotdogvulkin.github.io/Roboro-Capstone',{size:20,color:PINK,after:60}),
    body('Data current through August 2026. Figures describing unenacted budgets are stated as of that date.',
      {size:18,color:MUTED}),
    rule(),

    // ---- problem ----
    h1('The Problem'),
    body('As of August 2026, North Carolina has been operating without a complete budget since July 2025 — more than a year. Pennsylvania has missed its deadline in 10 of the last 13 fiscal years. Massachusetts has never once enacted its budget on time across all 13 years in this dataset. These are not anomalies. They are settled behaviour.'),
    body('Five states entered fiscal year 2027 with no enacted budget at all: Massachusetts, Michigan, North Carolina, Pennsylvania and South Carolina. The national on-time rate has sat between 84% and 88% for five years, well below the 95% recorded in FY2015.'),
    body('This paper presents a 50-state, 13-year analysis of budget timing. The finding is not that budget delay is spreading. It is that delay is concentrated in a stable, identifiable set of states — and that being concentrated is exactly what makes it predictable.'),

    // ---- thesis ----
    h1('The Thesis'),
    body('Budget lateness is not getting worse nationally, and it is not partisan. It is structural, it is concentrated, and it is forecastable a year ahead.'),
    body('That matters more than a worsening trend would. A deteriorating national average would be a story about the country. A stable set of chronically late states is something an organization can plan around — if it knows which states, and when in the session to start watching.'),
    body('The data does not say one party is worse. It says the process is under structural stress in states with full-time, professional legislatures, regardless of who controls them.'),

    // ---- size ----
    h1('The Stakes Are Larger in Nominal Terms'),
    stat('+32%','Per-capita spending growth, FY2015–FY2024 (nominal)'),
    stat('$8,955','National per-capita state spending, FY2024'),
    stat('0%','The same growth, adjusted for inflation'),
    body('National per-capita state spending grew from $6,786 to $8,955 between FY2015 and FY2024 — a 32% nominal increase. In real terms, after adjusting by the BLS CPI-U, per-capita growth is flat. The entire increase is inflation and population.'),
    body('That distinction should be stated plainly, because it cuts against the easy version of this argument: states are not spending more per person than they did a decade ago. There is no growing pot being fought over.'),
    body('What has grown is the nominal size of the appropriations bills themselves. Legislators, lobbyists and budget officers negotiate in nominal dollars, and a one-month delay in 2024 freezes 32% more spending authority than the same delay in 2015. The stakes per day of delay are larger even though the real budget is not.'),
    body('The range across states is wide: Alaska spends $19,369 per capita, Texas $4,621. That reflects policy choices and structural differences — Medicaid expansion, federal land payments, resource revenue. The nominal upward trend is near-universal: 47 of 50 states spent more per capita in FY2024 than in FY2015 before adjusting for inflation.'),

    // ---- later ----
    h1('Lateness Is Concentrated, Not Growing'),
    ...figure('chart_trend.png',1000,560,
      'Figure 1 — National on-time rate, FY2015–FY2027. Computed from 577 budget decisions; two-year carryovers excluded.'),
    body('The national on-time rate peaked at 95% in FY2015, fell through the late 2010s, dipped to 74% in FY2021 under COVID, and has since settled in a band between 84% and 88%. It has not recovered to its earlier level, and it is not deteriorating either.'),
    body('Tested directly, the within-state trend in days-late is +0.05 days per year (p = 0.90) — indistinguishable from flat. Between 2 and 11 states miss in any given year, and 28 of the 50 have never missed once.'),
    h2('The chronic offenders'),
    body('Massachusetts — 13 of 13 fiscal years late, the only state that has never made its deadline. Lateness ranges from 3 to 163 days. Interim budgets are routine rather than emergency measures. The FY2021 budget was not signed until 11 December 2020, 163 days into the fiscal year.'),
    body('Pennsylvania — 10 of 13 late, averaging 51 days. FY2016 ran 271 days past the deadline, enacted in March 2016. FY2021 was 145 days late, FY2026 was 134. As of August 2026 the FY2027 deadline has passed unmet: a fifth consecutive miss.'),
    body('North Carolina — 9 of 11 tracked years late, averaging 45 days, including four fiscal years with no complete budget at all: FY2020, FY2021, FY2026 and FY2027. The state has run more than a year on continuing authority from prior appropriations.'),
    body('New York — deteriorating on a consistent trajectory: 8 days late in FY2023, 32 in FY2024, 21 in FY2025, 49 in FY2026, 57 in FY2027. An April 1 fiscal year start pushes those enactments into late May.'),
    body('Illinois — the counter-example. A budget impasse that left FY2016 with no enacted budget at all gave way to eight consecutive on-time budgets from FY2020 to FY2027. Dysfunction can be severe, and it can also reverse.'),

    // ---- predicts ----
    h1('What Predicts Lateness'),
    ...figure('chart_legislature.png',1000,560,
      'Figure 2 — On-time enactment by legislature type, across 577 budget decisions.'),
    body('The strongest predictor is legislature type. Full-time professional legislatures miss 34% of the time; part-time citizen legislatures miss 4% — a ratio of roughly 8 to 1, significant at p = 0.0003 across 577 comparable budget decisions.'),
    body('The mechanism is the calendar, not the politics. Part-time legislatures sit for 30 to 90 days, pass a budget and adjourn; there is no time for an extended negotiation and no way to avoid the vote. Full-time legislatures can always sit another week, so disagreement converts into delay instead of compromise.'),
    body('The clearest evidence for that reading is an interaction. Divided government in a part-time legislature produces a 0% miss rate across five states. The same divided government in a full-time legislature produces 46%. Identical political conflict, opposite outcomes — the difference is whether anything forces the session to end.'),
    h2('What does not predict lateness'),
    bullet('Party control — divided versus unified, p = 0.95.'),
    bullet('Party direction — Republican-trifecta states miss 4.7% against 22.4% for Democratic trifectas (p = 0.002), but 62.5% of Democratic trifecta states have full-time legislatures against 8.7% of Republican ones. Control for that and party is worth nothing (p = 0.74). It was legislature professionalism wearing a party label.'),
    bullet('State population — p = 0.91 once legislature type is controlled for.'),
    bullet('Budget cycle — annual versus biennial, p = 0.27.'),
    bullet('Fiscal stress — real per-capita spending growth, p = 0.47. States in real contraction enacted earlier, not later.'),
    body('Budget fights are about disagreement, not scarcity.',{before:60}),

    // ---- predictable ----
    h1('Lateness Is Predictable'),
    body('Budget timing is unpredictable year to year and highly predictable state to state. 65% of the variance in days-late is between states rather than within them.'),
    body('Raw year-to-year autocorrelation looks strong (r = 0.58), but it is entirely compositional. Once each state’s own historical average is removed, last year’s result carries no additional information (p = 0.43, permutation test). Recency is noise; the track record is signal.'),
    body('A state that has missed in a majority of its prior years misses again 80% of the time, against a 15% base rate — a 5.2× lift, scored walk-forward using only earlier data. Shrinking each state’s rate toward the base rate for its legislature type improves that to 82% precision at 5.3× lift, validated on 427 state-years.'),
    ...figure('chart_watchlist.png',1000,620,
      'Figure 3 — Highest-risk states for FY2028. Scored from prior years only.'),

    // ---- overrun ----
    h1('Session Overrun: The Early Warning'),
    body('Every signal above is a prior — what a state tends to do before the session starts. One signal moves while the outcome is still undecided: how far past its scheduled adjournment a legislature keeps sitting.'),
    body('Across 410 sessions in 44 states, each day past scheduled adjournment adds 0.25 days of budget delay (p < 0.001, state fixed effects). A legislature a month past its scheduled close enacts its budget about seven days later than that state’s own norm. The relationship is a threshold rather than a dial: a fortnight over is ordinary, a month over is the alarm.'),
    body('One limitation is structural and severe. Six states — Massachusetts, Michigan, New Jersey, New York, Ohio and Wisconsin — never schedule an adjournment date at all, so they cannot overrun one. Those are precisely the states where lateness is most common. A legislature that never has to go home is never running late. For them the early warning has to come from bill-level tracking rather than the session calendar.'),

    // ---- costs ----
    h1('What Budget Delays Cost'),
    body('A late budget does not have the same consequence everywhere — some states continue on prior-year authority, others pass interim budgets, a few stop payments — but the exposure is consistent in kind:'),
    bullet('Agencies face hiring freezes, contract delays and paused grant disbursement. Programs cannot start and posts cannot be filled.'),
    bullet('Contractors and vendors face payment uncertainty and cash-flow disruption, with small vendors disproportionately affected.'),
    bullet('Advocacy organizations cannot plan legislative strategy against an unknown timeline. Tracking an appropriations line item requires knowing not just whether a budget will pass but when.'),
    bullet('Credit rating agencies treat budget timeliness as a governance signal, and chronic lateness draws repeated analyst commentary.'),

    // ---- case ----
    h1('The Case for Legislative Intelligence'),
    body('The organizations that handle budget uncertainty best are the ones with real-time visibility into the process — not "is the budget done?" but "where is the appropriations bill, which committee holds it, what was filed today, and what does the timeline look like?"'),
    body('This analysis was built by manually sourcing 651 enactment dates across 50 states and 13 fiscal years, cross-referencing NASBO reports, governors’ press archives and state session laws, and auditing every row against independent sources. That took an entire summer, and it produced a picture that is accurate as of one date and begins ageing immediately.'),
    body('The signals it identifies — track record, legislature type, session overrun — are all things a platform can watch continuously rather than reconstruct once a year.'),

    // ---- methodology ----
    h1('Methodology'),
    body('Budget timing. 651 state-fiscal-years spanning FY2014–FY2027, sourced from NASBO Summaries of Proposed & Enacted Budgets, governors’ press archives, state session-law records and contemporaneous reporting. 575 rows (88%) carry an exact signing date verified against primary sources; 67 (10%) are dated to the month where no source gives the day; 9 record confirmed no-budget years. 577 rows are budget decisions a legislature actually made; the remaining 74 are years covered by a two-year budget passed in an earlier session, and are excluded from every statistic.',{size:20}),
    body('Budget size. Total state expenditures from NASBO State Expenditure Report via KFF (FY2024) and Tax Policy Center / Census Annual Survey of State Government Finances (FY2015–FY2023). Population from Census estimates. Inflation adjustment by BLS CPI-U annual averages.',{size:20}),
    body('Session overrun. 410 sessions across 44 states, FY2015–FY2026, built by comparing two vintages of the NCSL Legislative Session Calendar — an early-season edition giving scheduled adjournment and a post-session edition giving actual sine die — so the scheduled date is a contemporaneous forecast rather than a reconstruction.',{size:20}),
    body('Statistical tests. Group comparisons by Mann-Whitney U, with Welch t-tests run alongside and agreeing on sign. Legislature-type and party effects by ordinary least squares at the state level. Session overrun by OLS with a dummy per state. Autocorrelation by within-state demeaned lag-1 correlation with a 5,000-draw permutation test to remove the mechanical negative bias demeaning induces. The unit of analysis is the state for group comparisons and the state-year for correlations. All p-values are two-sided.',{size:20}),
    body('Reproducibility. Every figure in this paper is regenerated from the published datasets by analysis/budget_timing_predictive_analysis.py in the project repository. The three charts are generated by analysis/make_paper_charts.py from the same CSVs the dashboard reads.',{size:20}),
    rule(),
    body('Interactive dashboard and full data: hotdogvulkin.github.io/Roboro-Capstone',{size:20,color:PINK}),
  ]}]
});

Packer.toBuffer(doc).then(b=>{
  const out='/Users/grantgarcia/Desktop/Roboro_Whitepaper_Budget_Timing_v2.docx';
  fs.writeFileSync(out,b);
  console.log('wrote', out, (b.length/1024).toFixed(0)+'KB');
});
