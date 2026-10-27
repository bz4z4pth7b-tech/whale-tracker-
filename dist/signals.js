(function(root){
'use strict';
const defaults={shares:100000,dollars:0,includeChanges:false,followedOnly:false,followed:['1067983','1336528','1649339','1037389','1423053','1350694','1603466']};
function settings(value={}){const positive=(v,d)=>Number.isFinite(Number(v))&&Number(v)>=0?Number(v):d;return {...defaults,shares:positive(value.shares,defaults.shares),dollars:positive(value.dollars,0),includeChanges:value.includeChanges===true,followedOnly:value.followedOnly===true,followed:Array.isArray(value.followed)?[...new Set(value.followed.map(String))]:[...defaults.followed]};}
function isFollowed(e,p){return [String(e.cik||''),...(e.owner_ciks||[]).map(String)].some(c=>p.followed.includes(c));}
function matches(e,p){if(p.followedOnly&&!isFollowed(e,p))return false;let n;if(e.kind==='disclosed_purchase')n=e.shares;else if(e.kind==='reported_position_increase'&&p.includeChanges)n=e.shares_added;else return false;if(!Number.isFinite(n)||n<=p.shares)return false;if(p.dollars>0&&(!Number.isFinite(e.amount)||e.amount<=p.dollars))return false;return true;}
function recent(e,days,now=Date.now()){const t=Date.parse(e.filed);return Number.isFinite(t)&&Math.floor(now/86400000)-Math.floor(t/86400000)>=0&&Math.floor(now/86400000)-Math.floor(t/86400000)<days;}
function buying(events,days=7,now=Date.now()){
 const groups=new Map(),seen=new Set();for(const e of events){if(seen.has(e.id)||e.kind!=='disclosed_purchase'||!recent(e,days,now))continue;seen.add(e.id);const key=(e.symbol||e.issuer)+'|'+e.security;if(!groups.has(key))groups.set(key,{symbol:e.symbol||'—',issuer:e.issuer,security:e.security,shares:0,known_dollars:0,missing_prices:0,reports:0,owners:new Set(),latest:e.filed});const g=groups.get(key);g.shares+=e.shares;g.reports++;for(const c of e.owner_ciks||[])g.owners.add(c);if(Number.isFinite(e.amount))g.known_dollars+=e.amount;else g.missing_prices++;if(e.filed>g.latest)g.latest=e.filed;}
 return [...groups.values()].map(g=>({...g,owners:g.owners.size})).sort((a,b)=>b.known_dollars-a.known_dollars||b.shares-a.shares);
}
function hot(rows,mode='volume'){const valid=rows.filter(s=>Number.isFinite(s.relative_volume)&&Number.isFinite(s.change));const score=s=>mode==='gainers'?s.change:mode==='turnover'?(s.daily_dollar_volume||0):s.relative_volume;return [...valid].sort((a,b)=>score(b)-score(a));}
function newNotifications(events,previous,initialized,p,now=Date.now()){
 const seen=new Set(previous);return initialized?events.filter(e=>!seen.has(e.id)&&matches(e,p)&&recent(e,2,now)):[];
}
const api={defaults,settings,isFollowed,matches,buying,hot,newNotifications};if(typeof module!=='undefined')module.exports=api;else root.WhaleSignals=api;
})(typeof globalThis!=='undefined'?globalThis:this);
