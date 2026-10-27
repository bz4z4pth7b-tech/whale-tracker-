"""SEC disclosures: reported purchases and quarter-end holdings, never live order flow."""
import hashlib, json, math, os, re, time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

DEFAULT_AGENT='WhaleEdgeResearch/2.0 (+https://github.com/bz4z4pth7b-tech/whale-tracker-/issues)'
ROOT=Path(__file__).resolve().parents[1]

class SEC:
    def __init__(self):
        self.agent=os.getenv('SEC_USER_AGENT') or DEFAULT_AGENT
        self.last=0; self.requests=0; self.blocked=set()
    def text(self,url):
        if not re.match(r'^https://(www|data)\.sec\.gov/',url): raise ValueError('Only SEC URLs allowed')
        host=urllib.parse.urlparse(url).netloc
        if host in self.blocked: raise RuntimeError('SEC host blocked this refresh; no retries')
        time.sleep(max(0,.2-(time.monotonic()-self.last)))
        req=urllib.request.Request(url,headers={'User-Agent':self.agent,'Accept':'application/json,application/xml,text/plain,*/*'})
        self.last=time.monotonic();self.requests+=1
        try:
            with urllib.request.urlopen(req,timeout=20) as r: return r.read(20_000_000).decode('utf-8-sig')
        except urllib.error.HTTPError as e:
            if e.code in (403,429): self.blocked.add(host)
            raise
    def json(self,url): return json.loads(self.text(url))

def xml(text):
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper(): raise ValueError('External XML entities are not accepted')
    root=ET.fromstring(text)
    for n in root.iter(): n.tag=n.tag.rsplit('}',1)[-1]
    return root

def val(node,path,default=''): return node.findtext(path,default).strip()
def number(s):
    if not s: return None
    try: n=float(s.replace(',',''))
    except ValueError: return None
    return n if math.isfinite(n) and n>=0 else None

def parse_form4(text,meta):
    root=xml(text)
    if root.tag!='ownershipDocument': raise ValueError('Not an ownership document')
    if val(root,'documentType')!='4': return [] # amendments require explicit reconciliation
    owners=[{'name':val(n,'reportingOwnerId/rptOwnerName'),'cik':val(n,'reportingOwnerId/rptOwnerCik').lstrip('0') or '0'} for n in root.findall('reportingOwner')]
    symbol=val(root,'issuer/issuerTradingSymbol');issuer=val(root,'issuer/issuerName')
    groups={}
    for n in root.findall('nonDerivativeTable/nonDerivativeTransaction'):
        if val(n,'transactionCoding/transactionCode')!='P' or val(n,'transactionAmounts/transactionAcquiredDisposedCode/value')!='A': continue
        shares=number(val(n,'transactionAmounts/transactionShares/value'));price=number(val(n,'transactionAmounts/transactionPricePerShare/value'))
        if shares is None or shares<=0:continue
        when=val(n,'transactionDate/value');security=val(n,'securityTitle/value');ownership=val(n,'ownershipNature/directOrIndirectOwnership/value')
        key=(when,security,ownership)
        g=groups.setdefault(key,{'shares':0,'amount':0,'priced':True,'lines':0})
        g['shares']+=shares;g['lines']+=1
        if price is None:g['priced']=False
        else:g['amount']+=shares*price
    out=[]
    for (when,security,ownership),g in groups.items():
        ident=hashlib.sha256(f"{meta['accession']}|{when}|{security}|{ownership}".encode()).hexdigest()[:20]
        out.append({**meta,'id':'purchase-'+ident,'kind':'disclosed_purchase','manager':' / '.join(o['name'] for o in owners),'owner_ciks':[o['cik'] for o in owners],'symbol':symbol,'issuer':issuer,'security':security,'transaction_date':when,'shares':g['shares'],'amount':g['amount'] if g['priced'] else None,'ownership':ownership,'line_count':g['lines'],'label':'Reported purchase · Form 4 code P','caveat':'Open-market or private purchase as filed; not a live trade. Original reports can later be amended. Joint reporting owners are not counted as separate purchases.'})
    return out

class NotInformationTable(ValueError):
    """A valid XML attachment that is not a holdings information table."""

def parse_holdings(text):
    root=xml(text); result={}
    nodes=list(root.iter('infoTable'))
    if not nodes:
        if root.tag == 'informationTable':
            raise ValueError('No information-table rows found')
        raise NotInformationTable('Not an information-table attachment')
    for n in nodes:
        # Option-underlying share counts and principal amounts are not stock shares.
        if val(n,'putCall') or val(n,'shrsOrPrnAmt/sshPrnamtType')!='SH':continue
        cusip=val(n,'cusip');share_class=val(n,'titleOfClass');shares=number(val(n,'shrsOrPrnAmt/sshPrnamt'))
        if not cusip or shares is None:raise ValueError('Invalid information-table share row')
        key=cusip+'|'+share_class
        r=result.setdefault(key,{'cusip':cusip,'security':share_class,'issuer':val(n,'nameOfIssuer'),'shares':0})
        r['shares']+=shares
    return result

def adjacent_periods(a,b):
    try:
        x=date.fromisoformat(a);y=date.fromisoformat(b)
        return x.month in (3,6,9,12) and y.month in (3,6,9,12) and 70<=(x-y).days<=100
    except ValueError:return False

def compare_holdings(current,previous,meta):
    if meta.get('amended') or not adjacent_periods(meta['period'],meta['previous_period']):return []
    changes=[]
    for key,r in current.items():
        old=previous.get(key,{}).get('shares',0);delta=r['shares']-old
        if delta<=0:continue
        changes.append({**meta,**r,'id':'holding-'+hashlib.sha256((meta['accession']+'|'+key).encode()).hexdigest()[:20],'kind':'reported_position_increase','previous_shares':old,'shares_added':delta,'amount':None,'label':'New reported position' if old==0 else 'Reported share increase','caveat':'Quarter-end share change, not a verified purchase. Splits, transfers and reporting changes can alter counts; no split adjustment applied.'})
    return sorted(changes,key=lambda x:x['shares_added'],reverse=True)

def feed_entries(text):
    root=xml(text);out=[]
    for e in root.findall('entry'):
        cat=e.find('category');form=cat.get('term','') if cat is not None else ''
        link=e.find('link');url=link.get('href','') if link is not None else ''
        match=re.search(r'/data/(\d+)/(?:\d+/)?(\d{10}-\d{2}-\d{6})-index\.htm',url)
        if not match:continue
        cik,acc=match.groups();out.append({'form':form,'accession':acc,'cik':cik,'accepted':val(e,'updated'),'filed':val(e,'updated')[:10],'url':url})
    return out

def cached(path,producer):
    if path.exists():return json.loads(path.read_text())
    x=producer();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(x,allow_nan=False));return x

def document_urls(sec,meta):
    base=f"https://www.sec.gov/Archives/edgar/data/{int(meta['cik'])}/{meta['accession'].replace('-','')}/"
    items=sec.json(base+'index.json')['directory']['item']
    return [base+item['name'] for item in items if item['name'].endswith('.xml') and '/' not in item['name']]

def ownership(sec,meta):
    for url in document_urls(sec,meta):
        text=sec.text(url)
        try:
            if xml(text).tag=='ownershipDocument':return parse_form4(text,{**meta,'url':url})
        except ET.ParseError:continue
    raise ValueError('Form 4 XML not found')

def holdings(sec,meta):
    combined={};found=False
    for url in document_urls(sec,meta):
        text=sec.text(url)
        try: rows=parse_holdings(text)
        except NotInformationTable:continue
        found=True
        for key,row in rows.items():
            if key not in combined:combined[key]=dict(row)
            else:combined[key]['shares']+=row['shares']
    if not found:raise ValueError('13F information table not found')
    return combined

def manager_data(sec,manager,cache):
    cik=str(int(manager['cik']));r=sec.json(f'https://data.sec.gov/submissions/CIK{int(cik):010d}.json');recent=r['filings']['recent'];records=[]
    for i,form in enumerate(recent['form']):
        if form not in ('13F-HR','13F-HR/A'):continue
        records.append({'manager':r['name'],'cik':cik,'form':form,'filed':recent['filingDate'][i],'period':recent['reportDate'][i],'accepted':recent['acceptanceDateTime'][i],'accession':recent['accessionNumber'][i],'url':f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{recent['accessionNumber'][i].replace('-','')}/{recent['primaryDocument'][i]}"})
    bases=sorted((x for x in records if x['form']=='13F-HR'),key=lambda x:(x['period'],x['filed']),reverse=True)
    base=next(iter(bases),None)
    result={**manager,'name':r['name'],'cik':cik,'status':'ok','holdings':[],'changes':[],'filings':records[:4]}
    if not base:return {**result,'status':'no_13f','note':'No 13F-HR in recent SEC submission history.'}
    amended=any(x['form']=='13F-HR/A' and x['period']==base['period'] for x in records)
    current=cached(cache/(base['accession']+'.holdings.json'),lambda:holdings(sec,base))
    result.update({'period':base['period'],'filed':base['filed'],'url':base['url'],'holdings_count':len(current),'holdings':sorted(current.values(),key=lambda x:x['shares'],reverse=True)[:30],'amended':amended,'note':'Top 30 reported share positions by share count, not dollar weight. Options and principal amounts excluded.'})
    previous=next((x for x in bases if x['period']<base['period']),None)
    if amended:result.update(status='amendment_review',note='Amendment exists. Original holdings shown; changes suppressed until reconciliation.')
    elif previous:
        previous_amended=any(x['form']=='13F-HR/A' and x['period']==previous['period'] for x in records)
        if previous_amended:result.update(status='amendment_review',note='Previous period amended; changes suppressed until reconciliation.')
        else:
            old=cached(cache/(previous['accession']+'.holdings.json'),lambda:holdings(sec,previous))
            changes=compare_holdings(current,old,{**base,'previous_period':previous['period'],'amended':False})
            result.update({'changes':changes[:200],'changes_count':len(changes),'previous_period':previous['period']})
    return result

def collect(config,prior):
    sec=SEC();cache=ROOT/'data/sec-cache';errors=[];managers=[];filings=[];events=[]
    old={str(int(m['cik'])):m for m in prior.get('managers',[])}
    for m in config['managers']:
        try:
            result=manager_data(sec,m,cache);managers.append(result);filings.extend(result['filings']);events.extend(result['changes'])
        except Exception as e:
            errors.append(f"SEC manager {m['name']}: {type(e).__name__}: {e}")
            managers.append({**old.get(str(int(m['cik'])),m),'status':'unavailable','note':'Refresh failed. Any retained holdings are dated historical observations.'})
    purchase_coverage={'limit':40,'description':'Newest 100 Form 4 feed entries; at most 40 non-amended filings parsed per refresh. Not all insiders or all transactions.'}
    try:
        feed=sec.text('https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only&count=100&output=atom')
        entries=[e for e in feed_entries(feed) if e['form']=='4'][:40];parsed=0
        for meta in entries:
            try:
                events.extend(cached(cache/(meta['accession']+'.purchases.json'),lambda m=meta:ownership(sec,m)));parsed+=1
            except Exception as e:errors.append(f"SEC purchase {meta['accession']}: {type(e).__name__}: {e}")
        purchase_coverage.update({'feed_filings':len(entries),'parsed_filings':parsed,'status':'ok' if parsed==len(entries) and entries else 'partial' if parsed else 'unavailable'})
    except Exception as e:
        errors.append(f'SEC purchase feed: {type(e).__name__}: {e}');purchase_coverage['status']='unavailable'
    # Retain stable event IDs across refreshes. No browser action rewrites source history.
    merged={e['id']:e for e in prior.get('whale_events',[]) if e.get('id')}
    merged.update({e['id']:e for e in events})
    events=sorted(merged.values(),key=lambda e:(e.get('filed',''),e.get('id','')),reverse=True)[:5000]
    return {'managers':managers,'whales':filings or prior.get('whales',[]),'whale_events':events,'purchase_coverage':purchase_coverage,'errors':errors,'status':'ok' if not errors else 'partial' if filings or events else 'unavailable','requests':sec.requests}

