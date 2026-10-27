const assert=require('node:assert/strict');const S=require('../dist/signals.js');const p=S.settings({shares:100000});const e={id:'x',kind:'disclosed_purchase',shares:100001,amount:200000,owner_ciks:['1067983'],filed:'2026-10-27',symbol:'TEST',issuer:'Fixture',security:'Common'};let n=0;function test(name,fn){fn();n++;console.log('PASS '+name)}
test('Threshold is strictly over, not equal',()=>{assert(S.matches(e,p));assert(!S.matches({...e,shares:100000},p))});
test('Unknown purchase amount cannot pass dollar threshold',()=>assert(!S.matches({...e,amount:null},S.settings({dollars:1}))))
test('Holdings changes are excluded from purchase-only alerts',()=>assert(!S.matches({...e,kind:'reported_position_increase',shares_added:100001},p)))
test('Holdings can be explicitly enabled',()=>assert(S.matches({...e,kind:'reported_position_increase',shares_added:100001},S.settings({includeChanges:true}))))
test('Following uses CIK, not name',()=>{assert(S.matches(e,S.settings({followedOnly:true})));assert(!S.matches(e,S.settings({followedOnly:true,followed:[]})))})
test('No retroactive notification flood on first visit',()=>assert.equal(S.newNotifications([e],[],false,p,Date.parse('2026-10-27T12:00:00Z')).length,0))
test('Repeated snapshots do not notify twice',()=>assert.equal(S.newNotifications([e],['x'],true,p,Date.parse('2026-10-27T12:00:00Z')).length,0))
test('Fresh unseen matching event notifies',()=>assert.equal(S.newNotifications([e],[],true,p,Date.parse('2026-10-27T12:00:00Z')).length,1))
test('Old filings do not notify on discovery',()=>assert.equal(S.newNotifications([{...e,filed:'2026-08-01'}],[],true,p,Date.parse('2026-10-27T12:00:00Z')).length,0))
test('Buying board deduplicates IDs and excludes holdings',()=>{const r=S.buying([e,e,{...e,id:'h',kind:'reported_position_increase'}],7,Date.parse('2026-10-27T12:00:00Z'));assert.equal(r[0].reports,1);assert.equal(r[0].shares,100001)})
test('Bad settings reset to safe defaults',()=>assert.equal(S.settings({shares:-5}).shares,100000))
test('Hot rank does not mutate source data',()=>{const r=[{relative_volume:1,change:.1},{relative_volume:3,change:-.2}];assert.equal(S.hot(r)[0].relative_volume,3);assert.equal(r[0].relative_volume,1)})
console.log(n+' signal and alert tests passed');
