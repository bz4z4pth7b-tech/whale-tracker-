"""Daily-bar research; no brokerage or execution capabilities."""
import math

def validate(bars):
    previous = ''
    for b in bars:
        if b['date'] <= previous: raise ValueError('Dates must be unique and increasing')
        previous = b['date']
        if any(not math.isfinite(b[k]) or b[k] <= 0 for k in ('open','high','low','close')): raise ValueError('Invalid OHLC')
        if b['low'] > min(b['open'],b['close']) or b['high'] < max(b['open'],b['close']): raise ValueError('Inconsistent OHLC')
        if not math.isfinite(b['volume']) or b['volume'] < 0: raise ValueError('Invalid volume')

STRATEGIES = ('breakout', 'momentum', 'pullback')
def signal(bars, i, strategy):
    if i < 21: return False
    b = bars[i]; past = bars[i-20:i]
    avgvol = sum(x['volume'] for x in past)/20
    liquid = sum(x['volume']*x['close'] for x in past)/20 >= 1_000_000
    if not liquid or not .25 <= b['close'] < 5 or avgvol <= 0: return False
    rv = b['volume']/avgvol
    ma = sum(x['close'] for x in past)/20
    if strategy == 'breakout': return b['close'] > max(x['high'] for x in past) and rv >= 1.5
    if strategy == 'momentum': return b['close']/bars[i-5]['close']-1 > .08 and rv >= 1.5
    if strategy == 'pullback': return b['close'] > ma and b['close'] < bars[i-1]['close'] and rv < 1.2
    raise ValueError('Unknown strategy')

def simulate(bars, strategy, start=21, end=None, cost_bps=50):
    validate(bars)
    if not 0 <= cost_bps < 10000: raise ValueError('Invalid cost')
    end = min(len(bars), end or len(bars)); cost=cost_bps/10000
    equity=1.; peak=1.; dd=0.; trades=[]; curve=[]; i=max(start,21)
    while i < end:
        if signal(bars,i,strategy) and i+6 < end:
            entry=i+1; exit_=i+6
            buy=bars[entry]['open']*(1+cost); sell=bars[exit_]['open']*(1-cost)
            # Mark to market during the holding period; include entry and exit costs.
            for j in range(entry,exit_):
                mark=equity*bars[j]['close']/buy*(1-cost)
                peak=max(peak,mark); dd=min(dd,mark/peak-1)
                curve.append({'date':bars[j]['date'],'equity':mark})
            r=sell/buy-1; equity*=1+r; peak=max(peak,equity); dd=min(dd,equity/peak-1)
            trades.append({'signal_date':bars[i]['date'],'entry_date':bars[entry]['date'],'exit_date':bars[exit_]['date'],'return':r})
            curve.append({'date':bars[exit_]['date'],'equity':equity}); i=exit_
        else:
            curve.append({'date':bars[i]['date'],'equity':equity}); i+=1
    wins=sum(max(t['return'],0) for t in trades); losses=-sum(min(t['return'],0) for t in trades)
    return {'return':equity-1,'drawdown':dd,'trades':trades,'curve':curve,'win_rate':sum(t['return']>0 for t in trades)/len(trades) if trades else None,'profit_factor':wins/losses if losses else None}

def research(history):
    # Fixed, equally funded symbol sleeves; unused sleeve capital stays in cash.
    usable={s:b for s,b in history.items() if len(b)>=180}
    if not usable: return {'status':'insufficient_history','strategies':[]}
    dates=sorted(set(b['date'] for bars in usable.values() for b in bars))
    split_date=dates[int(len(dates)*.6)]
    rows=[]
    for strategy in STRATEGIES:
        train=[]; test=[]; stress=[]
        for symbol,bars in usable.items():
            split=next((i for i,b in enumerate(bars) if b['date']>=split_date),len(bars))
            if split<30 or len(bars)-split<30: continue
            a=simulate(bars,strategy,end=split)
            b=simulate(bars,strategy,start=split)
            c=simulate(bars,strategy,start=split,cost_bps=150)
            for t in b['trades']: t['symbol']=symbol
            train.append(a);test.append(b);stress.append(c)
        if not test: continue
        n=len(test); trades=[t for x in test for t in x['trades']]
        # Reindex each sleeve to the common calendar before portfolio aggregation.
        timeline=sorted(set(p['date'] for x in test for p in x['curve']))
        maps=[{p['date']:p['equity'] for p in x['curve']} for x in test]
        last=[1.]*n; curve=[]; peak=1.; dd=0
        for d in timeline:
            last=[m.get(d,v) for m,v in zip(maps,last)]; eq=sum(last)/n
            peak=max(peak,eq);dd=min(dd,eq/peak-1);curve.append({'date':d,'equity':eq})
        wins=sum(max(t['return'],0) for t in trades);losses=-sum(min(t['return'],0) for t in trades)
        rows.append({'name':strategy,'train_return':sum(x['return'] for x in train)/n,'test_return':sum(x['return'] for x in test)/n,'stress_return':sum(x['return'] for x in stress)/n,'drawdown':dd,'trades':len(trades),'win_rate':sum(t['return']>0 for t in trades)/len(trades) if trades else None,'profit_factor':wins/losses if losses else None,'curve':curve,'trade_log':trades,'sleeves':n})
    champion=max(rows,key=lambda x:x['train_return'])['name'] if rows else None
    return {'status':'historical_research','split_date':split_date,'selection':'Highest training return; never selected on test returns','selected':champion,'strategies':rows,'cost_bps_one_way':50,'stress_bps_one_way':150,'hold_sessions':5,'limits':['Repeated inspection makes the holdout exploratory, not fresh validation.','Current watchlist has survivorship and selection bias; not an all-stock scan.','Adjusted-price penny classification can differ from historical traded prices.','No spread quotes, delisted history, halt, borrow or fill model; long-only, cash-funded.','No whale strategy is tested: filing publication timestamps and mapped holdings history are required.']}

def screen(symbol,bars):
    if len(bars)<22: return None
    b=bars[-1];past=bars[-21:-1];v=sum(x['volume'] for x in past)/20
    dv=sum(x['volume']*x['close'] for x in past)/20
    rv=b['volume']/v if v else 0
    reasons=[]
    if not .25<=b['close']<5: reasons.append('Outside $0.25–$5 band')
    if dv<1_000_000: reasons.append('Average daily dollar volume below $1M')
    return {'symbol':symbol,'date':b['date'],'price':b['close'],'change':b['close']/bars[-2]['close']-1,'relative_volume':rv,'dollar_volume':dv,'momentum':b['close']/bars[-6]['close']-1,'signals':[s for s in STRATEGIES if signal(bars,len(bars)-1,s)],'eligible':not reasons,'exclusions':reasons,'source':f'https://finance.yahoo.com/quote/{symbol}/history/'}
