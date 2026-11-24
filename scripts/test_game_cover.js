// Regression checks for priority covers and the DLC header's actual JPEG ratio.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const context = {
  document: {createElement: () => ({classList: {add() {}}, querySelector: () => ({textContent: ''})})},
  esc: s => String(s), phColor: () => '#000', firstChar: () => 'D'
};
vm.createContext(context);
vm.runInContext(html.slice(html.indexOf('const DAY_MS'), html.indexOf('/* 平台官方矢量')) +
  '\ntoday = readBeijingDay(new Date("2026-10-01T04:00:00Z"));', context);
vm.runInContext(html.slice(html.indexOf('const PICONS'), html.indexOf('function phColor')), context);   // card() 依赖内联平台图标表
vm.runInContext(html.slice(html.indexOf('function card('), html.indexOf('function firstChar(')), context);
vm.runInContext(html.slice(html.indexOf('function ckw('), html.indexOf('/* ---------- 电影')), context);
const cover = 'img/game_dd2_dark_arisen.jpg';
const fixture = {title: "Dragon's Dogma 2: Dark Arisen", cover_img: cover, year: 2026, month: 10, day: 9,
  plats: [{key: 'steam', name: 'Steam', img: 'https://example.test/ultrawide-package.jpg'}]};
assert(context.card(fixture).innerHTML.includes('class="cover" data-src="' + cover + '"'), 'Covers load on demand from data-src, priority cover first');
const names = new Set();
const image = {naturalWidth: 460, naturalHeight: 215, classList: {add: x => names.add(x)}};
context.ckw(image);
assert(!names.has('wide'), 'Normal DLC header must not use the letterboxed wide-banner mode');
context.ckw({...image, naturalWidth: 707, naturalHeight: 232});
assert(names.has('wide'), 'Existing wide-banner behavior must remain intact');
const bytes = fs.readFileSync(path.join(root, cover));
assert.equal(bytes.readUInt16BE(0), 0xffd8);
let dimensions;
for (let offset = 2; offset < bytes.length;) {
  assert.equal(bytes[offset++], 0xff);
  while (bytes[offset] === 0xff) offset++;
  const marker = bytes[offset++];
  if (marker === 0xd9 || marker === 0xda) break;
  if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) continue;
  const length = bytes.readUInt16BE(offset);
  assert(length >= 2 && offset + length <= bytes.length);
  if ([0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf].includes(marker)) {
    dimensions = {height: bytes.readUInt16BE(offset + 3), width: bytes.readUInt16BE(offset + 5)};
    break;
  }
  offset += length;
}
assert(dimensions && dimensions.width >= 400);
assert(dimensions.width / dimensions.height >= 1.7 && dimensions.width / dimensions.height <= 2.35);
const data = JSON.parse(fs.readFileSync(path.join(root, 'releases.json'), 'utf8'));
const listed = data.groups.flatMap(g => g.games).find(g => g.title === fixture.title);
if (listed) assert.equal(listed.cover_img, cover);
assert.equal(context.gameTitle('星球大战：银河赛车手™'), '星球大战：银河赛车手');
assert.equal(context.gameTitle('Star Wars® Galactic Racer™'), 'Star Wars Galactic Racer');
const noPrice = context.card({title: '测试', year: 2026, month: 10, day: 9,
  plats: [{key: 'ps', name: 'PS', url: 'https://example.test/'}]}).innerHTML;
assert(noPrice.includes('暂无价格'), 'A platform without price must say so instead of showing a bare icon');
const roundedPrices = context.card({...fixture, plats: [
  {key: 'steam', name: 'Steam', price: 208.6},
  {key: 'ps', name: 'PlayStation', price: 232.2},
  {key: 'ns', name: 'Nintendo Switch', price: 0}
]}).innerHTML;
assert(roundedPrices.includes('aria-label="Steam ¥209"') && roundedPrices.includes('¥209</a>'));
assert(roundedPrices.includes('aria-label="PlayStation HK$232"') && roundedPrices.includes('HK$232</a>'));
assert(roundedPrices.includes('aria-label="Nintendo Switch HK$0"') && roundedPrices.includes('HK$0</a>'));
console.log('Game cover valid: priority source, suitable JPEG ratio, unchanged wide-banner fallback, title symbols, rounded prices and missing prices');
