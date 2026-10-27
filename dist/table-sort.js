(function(root){
'use strict';
function value(text){const s=String(text??'').trim();if(!s||['—','Not disclosed','Unknown'].includes(s))return null;if(/^\d{4}-\d{2}-\d{2}$/.test(s))return Date.parse(s);const m=s.match(/^[+$−-]?[\d,]+(?:\.\d+)?(?:[%×])?(?:\s|$)/);if(m)return Number(m[0].trim().replace(/[$,%×+]/g,'').replace('−','-'));return s.toLowerCase();}
function compare(a,b,dir){if(a==null)return b==null?0:1;if(b==null)return -1;const c=typeof a==='number'&&typeof b==='number'?a-b:String(a).localeCompare(String(b),undefined,{numeric:true});return dir==='asc'?c:-c;}
function sort(rows,column,dir,text){return rows.map((r,i)=>({r,i,v:value(text(r[column]))})).sort((a,b)=>compare(a.v,b.v,dir)||a.i-b.i).map(x=>x.r);}
const api={value,compare,sort};if(typeof module!=='undefined')module.exports=api;else root.WhaleTableSort=api;
})(typeof globalThis!=='undefined'?globalThis:this);
