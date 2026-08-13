"""Parse an NCSL 'Legislative Session Calendar' PDF into
{state: (convene_text, adjourn_text, comments_text)} for the REGULAR session.

The PDFs are laid out as a 7-column table (State | Convene | Adjourn | Comments |
special Convene | special Adjourn | special Comments).  Column x-ranges are read off
the header row rather than hardcoded, because the layout shifts between years.
"""
import re, sys, pymupdf

STATES=["Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut",
"Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas",
"Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota",
"Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey",
"New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
"Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas",
"Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"]
FIRST={s.split()[0] for s in STATES}

def parse_pdf(path):
    doc=pymupdf.open(path)
    out={}
    for page in doc:
        ws=[w for w in page.get_text("words") if w[4].strip()]
        if not ws: continue
        # ---- locate header row: a y-band containing 'State','Convene','Adjourn'
        hdr=None
        byy={}
        for w in ws: byy.setdefault(round(w[1]/3),[]).append(w)
        for k,row in sorted(byy.items()):
            txt=[w[4] for w in row]
            if 'State' in txt and 'Convene' in txt and 'Adjourn' in txt:
                hdr=row; break
        if hdr is None: continue
        adj=[w for w in hdr if w[4]=='Adjourn']
        com=[w for w in hdr if w[4].startswith('Comment')]
        con=[w for w in hdr if w[4]=='Convene']
        if not adj or not con: continue
        adj.sort(key=lambda w:w[0]); com.sort(key=lambda w:w[0]); con.sort(key=lambda w:w[0])
        a0=adj[0][0]-10
        # keep the adjourn window well clear of the comments column: comment text
        # starts a little left of its own header, so split at 55% of the gap.
        a1=(adj[0][0]+0.55*(com[0][0]-adj[0][0])) if com else (adj[0][2]+40)
        c0=con[0][0]-10; c1=a0
        hy=hdr[0][3]
        # ---- state anchor rows
        anchors=[]
        for w in ws:
            if w[1]<hy: continue
            if w[0]>c0: continue
            if w[4].rstrip(',') in FIRST:
                nm=w[4].rstrip(',')
                if nm in ('New','North','South','West','Rhode'):
                    nxt=[x for x in ws if abs(x[1]-w[1])<4 and x[0]>w[2] and x[0]<c0]
                    if nxt: nm=nm+' '+sorted(nxt,key=lambda x:x[0])[0][4]
                if nm in STATES: anchors.append((w[1],nm))
        anchors.sort()
        for i,(y,nm) in enumerate(anchors):
            y1=anchors[i+1][0]-2 if i+1<len(anchors) else 1e9
            def grab(x0,x1,first_line_only=False):
                sel=[w for w in ws if x0<=w[0]<x1 and y-3<=w[1]<y1]
                sel.sort(key=lambda w:(round(w[1]/4),w[0]))
                if first_line_only and sel:
                    # An adjourn cell is always a single line ("June 15", "mid April",
                    # "Jan. 9, 2024").  Taking only the top line stops the last state on a
                    # page -- whose row band has no following anchor to close it -- from
                    # swallowing the footnotes and legend printed underneath the table.
                    top=round(sel[0][1]/4)
                    sel=[w for w in sel if round(w[1]/4)==top]
                return ' '.join(w[4] for w in sel).strip()
            # NB: only the REGULAR-session columns are read. The special-session cells are
            # vertically centred inside their row rather than top-aligned, so they do not
            # line up with the state anchors and cannot be attributed reliably.
            if nm not in out:
                out[nm]=(grab(c0,c1),grab(a0,a1,True),grab(a1,a1+130))
    return out

MON={'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,
     'nov':11,'dec':12,'january':1,'february':2,'march':3,'april':4,'june':6,'july':7,
     'august':8,'september':9,'october':10,'november':11,'december':12}
VAGUE={'early':5,'mid':15,'late':25,'end':28,'beginning':3}

def parse_date(txt,year):
    """-> (iso_date, precision) or (None, reason). precision: exact | approx"""
    if not txt or txt.strip() in ('*','',u'—','-','N/A','TBD'):
        return None,'no fixed adjournment'
    t=txt.replace('’',"'")
    t=re.sub(r'\s+',' ',t).strip()
    m=re.search(r'\b('+'|'.join(MON)+r')\w*\.?\s+(\d{1,2})(?:,?\s*(20\d\d))?',t,re.I)
    if m:
        mo=MON[m.group(1).lower()[:3] if m.group(1).lower()[:3] in MON else m.group(1).lower()]
        return f'{int(m.group(3) or year):04d}-{mo:02d}-{int(m.group(2)):02d}','exact'
    m=re.search(r'\b(early|mid|late|end of|beginning of)\s+('+'|'.join(MON)+r')\w*',t,re.I)
    if m:
        key=m.group(1).lower().split()[0]
        mo=MON[m.group(2).lower()[:3] if m.group(2).lower()[:3] in MON else m.group(2).lower()]
        return f'{year:04d}-{mo:02d}-{VAGUE[key]:02d}','approx'
    return None,'unparsed: '+t[:40]

if __name__=='__main__':
    for f in sys.argv[1:]:
        d=parse_pdf(f)
        yr=int(re.search(r'(20\d\d)',f).group(1))
        ok=sum(1 for s in d if parse_date(d[s][1],yr)[0])
        print(f'{f}: {len(d)}/50 states, {ok} adjourn dates parsed')
        for s in STATES[:6]+['Massachusetts','Pennsylvania','Maine']:
            if s in d: print(f'   {s:16} conv={d[s][0][:18]:20} adj={d[s][1][:22]:24} -> {parse_date(d[s][1],yr)}')
