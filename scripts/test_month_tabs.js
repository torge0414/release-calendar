// Lightweight DOM regression checks; no browser or third-party packages required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
for (const [, script] of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) new vm.Script(script);

function sourceBetween(start, end) {
  const first = html.indexOf(start);
  const last = html.indexOf(end, first + start.length);
  assert(first >= 0 && last > first, 'Missing source for ' + start);
  return html.slice(first, last);
}
const dateCode = sourceBetween('const DAY_MS', '/* 平台官方矢量');
const tabCode = sourceBetween('function setPageActive(', 'function visibleView(');
const imageCode = sourceBetween('function visibleView(', '/* 数据就位后淡出启动遮罩 */');
const loadCode = sourceBetween('function refreshPanel(', 'function stalePanels(');
const pageClasses = ['on', 'off'];

class Element {
  constructor() {
    this.children = [];
    this.attributes = {};
    this.handlers = {};
    this.names = new Set();
    this.style = {};
    this.offsetHeight = 100;
    this.classList = {
      add: (...names) => names.forEach(name => this.names.add(name)),
      remove: (...names) => names.forEach(name => this.names.delete(name)),
      contains: name => this.names.has(name),
      toggle: (name, on) => on ? this.names.add(name) : this.names.delete(name)
    };
  }
  set className(value) { this.names = new Set(value.split(/\s+/)); }
  replaceChildren(...children) { this.children = children; }
  appendChild(child) { this.children.push(child); return child; }
  addEventListener(event, fn) { this.handlers[event] = fn; }
  setAttribute(key, value) { this.attributes[key] = value; }
}

const groupData = (months, key) => months.map(([year, month])=>({year, month, [key]: []}));

function fixture(months, now, saved = {}, autoRender = true) {
  const memory = new Map(Object.entries(saved));
  const tabs = new Element();
  tabs.id = 'tabs';
  const title = new Element();
  const views = [new Element(), new Element()];
  const panels = ['games', 'albums'].map((key, i)=>{
    const body = new Element();
    body.parentElement = views[i];
    return {
      key, body, url: key + '.json', error: new Element(),
      groups: autoRender ? groupData(months, key) : null,
      makeCard: () => new Element(),
      footer: count => String(count)
    };
  });
  const context = {
    now,
    document: {createElement: () => new Element(), getElementById: id => id === 'mhMn' ? title : null},
    sessionStorage: {
      getItem: key => memory.get(key) || null,
      setItem: (key, value) => memory.set(key, value),
      removeItem: key => memory.delete(key)
    },
    visibleView: () => views[0],
    moveGlider() {}, stackFit() {}, wakeVisible() {}, hideBoot() {}, scheduleDateCheck() {},
    esc: String, setTimeout: () => 0, clearTimeout() {},
    animSwap: (cur, next) => { cur.classList.remove('on'); cur.classList.add('off'); next.classList.remove('off'); next.classList.add('on'); },
    PAGE_CLASSES: pageClasses
  };
  vm.createContext(context);
  vm.runInContext(dateCode + tabCode + '\ntoday = readBeijingDay(new Date(now));', context);
  const calendar = context.tabbed(tabs, panels);
  context.calendar = calendar;
  if (autoRender) panels.forEach(calendar.render);
  return {tabs, title, panels, memory, calendar, context};
}

function assertActive(f, index) {
  for (const p of f.panels) {
    p.sections.forEach((section, i)=>{
      assert.equal(section.classList.contains('on'), i === index);
      assert.equal(section.inert, i !== index);
      assert.equal(section.attributes['aria-hidden'], String(i !== index));
    });
  }
  f.tabs.children.forEach((button, i)=>assert.equal(button.attributes['aria-pressed'], String(i === index)));
}

const months = [[2026, 9], [2026, 10], [2026, 11]];
const october = '2026-10-01T04:00:00Z';
const normal = fixture(months, october, {glwTab_tabs: '0'});
assert.deepEqual(normal.tabs.children.map(c=>c.textContent), ['上月', '本月', '下月']);
assertActive(normal, 1);
normal.tabs.children[2].handlers.click();
assertActive(normal, 2);
assert.equal(normal.memory.get('glwTab_tabs_month'), '2026-11');
normal.tabs.children[0].handlers.click();
assertActive(normal, 0);
normal.tabs.children[1].handlers.click();
assertActive(normal, 1);
assert.equal(normal.memory.has('glwTab_tabs_month'), false, 'The current month follows the calendar');

const restored = fixture(months, october, {glwTab_tabs_month: '2026-11'});
assertActive(restored, 2);
assertActive(fixture(months, october, {glwTab_tabs_month: '2026-08'}), 1);
restored.tabs._switchBy(1);
assertActive(restored, 2);
restored.tabs._switchBy(-1);
assertActive(restored, 1);

const newYear = fixture([[2026, 11], [2026, 12], [2027, 1]], '2026-12-31T15:59:00Z');
assert.equal(newYear.title.textContent, '12');
const tabButtons = newYear.tabs.children.slice();
newYear.context.now = '2026-12-31T16:00:00Z';
vm.runInContext('today = readBeijingDay(new Date(now)); calendar.updateDay();', newYear.context);
assert.equal(newYear.title.textContent, '01');
assert.equal(vm.runInContext('releaseOffset({year:2027, month:1, day:1})', newYear.context), 0);
assert.equal(vm.runInContext('releaseOffset({year:2026, month:12, day:31})', newYear.context), -1);
assert.equal(newYear.calendar.hasCurrentWindow(newYear.panels[0]), false, 'The new next month can be pending');
assert.deepEqual(newYear.tabs.children, tabButtons, 'The same month buttons remain mounted on rollover');
assertActive(newYear, 1);

function testImages() {
  const image = src => ({
    dataset: {src}, removeAttribute: () => {}
  });
  const current = image('current.jpg'), otherMonth = image('other-month.jpg'), otherView = image('other-view.jpg');
  const view = (active, cover, hiddenCover) => ({
    classList: {contains: () => active},
    querySelector: selector => ({
      querySelectorAll: () => selector === '.sect.on' ? [cover] : [cover, hiddenCover]
    })
  });
  const stack = {children: [view(true, current, otherMonth), view(false, otherView)]};
  vm.runInNewContext(imageCode + '\nwakeVisible();', {document: {getElementById: () => stack}});
  assert.equal(current.src, 'current.jpg');
  assert.equal(otherMonth.src, undefined);
  assert.equal(otherView.src, undefined);
}

async function testLoads() {
  const f = fixture(months, october, {}, false);
  const [games, albums] = f.panels;
  const requests = [];
  f.context.fetch = url => new Promise(resolve=>requests.push({url, resolve}));
  vm.runInContext(loadCode, f.context);

  const loadingGames = f.context.refreshPanel(games);
  assert.equal(f.context.refreshPanel(games), loadingGames);
  const loadingAlbums = f.context.refreshPanel(albums);
  assert.equal(f.context.refreshPanel(albums), loadingAlbums);
  assert.deepEqual(requests.map(r=>r.url), ['games.json', 'albums.json']);

  requests[0].resolve({ok: true, json: async () => ({groups: groupData(months, 'games')})});
  await loadingGames;
  const gameSection = games.sections[1];
  requests[1].resolve({ok: true, json: async () => ({groups: groupData(months, 'albums')})});
  await loadingAlbums;
  assert.equal(games.sections[1], gameSection, 'Loading a category does not rebuild another category');
  assert.equal(f.context.refreshPanel(games), undefined);
  assertActive(f, 1);
}

testImages();
testLoads().then(()=>{
  console.log('Month tabs valid: shared selection, swipe, Beijing year rollover, deferred images, and isolated, deduplicated data loads');
}).catch(error=>{
  console.error(error);
  process.exitCode = 1;
});
