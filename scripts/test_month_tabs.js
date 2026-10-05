// Lightweight DOM regression checks; no browser or third-party packages required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
for (const [, script] of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) new vm.Script(script);
const code = html.slice(html.indexOf('function tabbed('), html.indexOf('function showCredit('));
class Element {
  constructor(){this.children=[];this.names=new Set();this.style={};this.handlers={};this.offsetHeight=100;this.offsetWidth=100;this.offsetLeft=3;
    this.classList={add:(...v)=>v.forEach(x=>this.names.add(x)),remove:(...v)=>v.forEach(x=>this.names.delete(x)),contains:v=>this.names.has(v),toggle:(v,on)=>on?this.names.add(v):this.names.delete(v)};
  }
  set className(value){this.names=new Set(value.split(/\s+/));}
  set innerHTML(value){this.children=[];}
  appendChild(child){this.children.push(child);return child;}
  addEventListener(event,fn){this.handlers[event]=fn;}
  querySelectorAll(){return this.children.filter(c=>c.names.has('tab'));}
}
function fixture(months,today,saved={}){
  const memory=new Map(Object.entries(saved));const window={addEventListener(){},removeEventListener(){}};
  const tabs=new Element();tabs.id='tabs';
  const panels=[1,2].map(()=>({body:new Element(),groups:months.map(([year,month])=>({year,month,games:[]})),makeCard:()=>new Element()}));
  const context={window,today,document:{createElement:()=>new Element(),getElementById:()=>null},localStorage:{getItem:key=>memory.get(key)||null,setItem:(key,value)=>memory.set(key,value)},moveGlider(){},stackFit(){},esc:s=>s,setTimeout:()=>0,clearTimeout(){},animSwap:(cur,nxt)=>{cur.classList.remove('on');cur.classList.add('off');nxt.classList.remove('off');nxt.classList.add('on');},PAGE_CLASSES:['on','off']};
  vm.createContext(context);vm.runInContext(code,context);context.tabbed(tabs,panels);
  return {tabs,panels,memory,window};
}
function active(p){return p.sections.findIndex(s=>s.classList.contains('on'));}
const months=[[2026,9],[2026,10],[2026,11]];
const normal=fixture(months,new Date(2026,9,1),{glwTab_tabs:'0'});
assert.deepEqual(normal.tabs.children.map(c=>c.textContent),['上月','本月','下月']);
for(const p of normal.panels){assert.equal(active(p),1);assert(p.sections[0].classList.contains('off'));assert(p.sections[2].classList.contains('off'));}
normal.tabs.children[2].handlers.click();
for(const p of normal.panels)assert.equal(active(p),2);
assert.equal(normal.memory.get('glwTab_tabs_month'),'2026-11');
normal.window._resetMonth_tabs();
for(const p of normal.panels)assert.equal(active(p),1);
const restored=fixture(months,new Date(2026,9,1),{glwTab_tabs_month:'2026-11'});
for(const p of restored.panels)assert.equal(active(p),2);
const expired=fixture(months,new Date(2026,9,1),{glwTab_tabs_month:'2026-08'});
for(const p of expired.panels)assert.equal(active(p),1);
const january=fixture([[2026,12],[2027,1],[2027,2]],new Date(2027,0,1));
assert.deepEqual(january.tabs.children.map(c=>c.textContent),['上月','本月','下月']);
console.log('Month tabs valid: labels, default current month, switching, reset, persistence and year boundary');
