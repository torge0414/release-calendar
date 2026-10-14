// Lightweight DOM regression checks; no browser or third-party packages required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
for (const [, script] of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) new vm.Script(script);
const code = html.slice(html.indexOf('function setPageActive('), html.indexOf('function showCredit('));
class Element {
  constructor(){this.children=[];this.names=new Set();this.style={};this.handlers={};this.offsetHeight=100;this.offsetWidth=100;this.offsetLeft=3;
    this.classList={add:(...v)=>v.forEach(x=>this.names.add(x)),remove:(...v)=>v.forEach(x=>this.names.delete(x)),contains:v=>this.names.has(v),toggle:(v,on)=>on?this.names.add(v):this.names.delete(v)};
  }
  set className(value){this.names=new Set(value.split(/\s+/));}
  set innerHTML(value){this.children=[];}
  appendChild(child){this.children.push(child);return child;}
  addEventListener(event,fn){this.handlers[event]=fn;}
  setAttribute(key,value){(this.attributes ||= {})[key]=value;}
  querySelectorAll(){return this.children.filter(c=>c.names.has('tab'));}
}
function fixture(months,today,saved={},games=()=>[]){
  const memory=new Map(Object.entries(saved));const local=new Map();const window={addEventListener(){},removeEventListener(){}};
  const tabs=new Element();tabs.id='tabs';
  const panels=[1,2].map(()=>({body:new Element(),groups:months.map(([year,month])=>({year,month,games:games(year,month)})),makeCard:()=>new Element()}));
  const context={window,today,document:{createElement:()=>new Element(),getElementById:()=>null},sessionStorage:{getItem:key=>memory.get(key)||null,setItem:(key,value)=>memory.set(key,value)},localStorage:{getItem:key=>local.get(key)||null,setItem:(key,value)=>local.set(key,value)},moveGlider(){},stackFit(){},esc:s=>s,setTimeout:()=>0,clearTimeout(){},animSwap:(cur,nxt)=>{cur.classList.remove('on');cur.classList.add('off');nxt.classList.remove('off');nxt.classList.add('on');},PAGE_CLASSES:['on','off']};
  vm.createContext(context);vm.runInContext(code,context);context.tabbed(tabs,panels);
  return {tabs,panels,memory,local,window};
}
function active(p){return p.sections.findIndex(s=>s.classList.contains('on'));}
function assertActive(f,index){
  for(const p of f.panels){
    assert.equal(active(p),index);
    p.sections.forEach((s,i)=>{
      assert.equal(s.inert,i!==index);
      assert.equal(s.attributes['aria-hidden'],String(i!==index));
    });
  }
  f.tabs.children.forEach((b,i)=>assert.equal(b.attributes['aria-pressed'],String(i===index)));
}
const months=[[2026,9],[2026,10],[2026,11]];
const normal=fixture(months,new Date(2026,9,1),{glwTab_tabs:'0'});
assert.deepEqual(normal.tabs.children.map(c=>c.textContent),['上月','本月','下月']);
assertActive(normal,1);
normal.tabs.children[2].handlers.click();
assertActive(normal,2);
assert.equal(normal.memory.get('glwTab_tabs_month'),'2026-11');
assert.equal(normal.local.get('glwTab_tabs_month'),undefined,'Month choice must only last for the session');
normal.tabs.children[0].handlers.click();
assertActive(normal,0);
normal.tabs.children[1].handlers.click();
assertActive(normal,1);
const restored=fixture(months,new Date(2026,9,1),{glwTab_tabs_month:'2026-11'});
assertActive(restored,2);
const expired=fixture(months,new Date(2026,9,1),{glwTab_tabs_month:'2026-08'});
assertActive(expired,1);
// 页底换月按钮和滑动入口
const navOf=section=>section.children.find(c=>c.names.has('mnav'));
const footer=fixture(months,new Date(2026,9,14));
assert.deepEqual(navOf(footer.panels[0].sections[1]).children.map(b=>b.textContent),['← 上月','下月 →']);
assert.deepEqual(navOf(footer.panels[0].sections[0]).children.map(b=>b.textContent),['本月 →']);
navOf(footer.panels[0].sections[1]).children[1].handlers.click();
assertActive(footer,2);
footer.tabs._switchBy(-1);
assertActive(footer,1);
footer.tabs._switchBy(-5);
assertActive(footer,1);
// 本月列表在今天的位置插入分隔线，其他月份不插
const days=(y,m)=>[2,10,14,20].map(day=>({year:y,month:m,day}));
const divided=fixture(months,new Date(2026,9,14),{},days);
const listOf=section=>section.children.find(c=>c.names.has('list'));
const lineAt=section=>listOf(section).children.findIndex(c=>c.names.has('today-line'));
assert.equal(lineAt(divided.panels[0].sections[1]),2,'Today line goes before the first item released today or later');
assert.equal(lineAt(divided.panels[0].sections[0]),-1);
assert.equal(lineAt(divided.panels[0].sections[2]),-1);
const allUpcoming=fixture(months,new Date(2026,9,1),{},days);
assert.equal(lineAt(allUpcoming.panels[0].sections[1]),-1,'No line when nothing has been released yet');
const january=fixture([[2026,12],[2027,1],[2027,2]],new Date(2027,0,1));
assert.deepEqual(january.tabs.children.map(c=>c.textContent),['上月','本月','下月']);
console.log('Month tabs valid: labels, default month, shared selection, inert hidden pages, accessible selection, session-only persistence, footer navigation, today line and year boundary');
