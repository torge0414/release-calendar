// Regression checks for priority covers and the DLC header's actual JPEG ratio.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const context = {
  today: new Date(2026, 9, 1),
  document: {createElement: () => ({classList: {add() {}}, querySelector: () => ({textContent: ''})})},
  esc: s => String(s), phColor: () => '#000', firstChar: () => 'D'
};
vm.createContext(context);
vm.runInContext(html.slice(html.indexOf('function card('), html.indexOf('function firstChar(')), context);
vm.runInContext(html.slice(html.indexOf('function ckw('), html.indexOf('/* ---------- 电影')), context);
const cover = 'img/game_dd2_dark_arisen.jpg';
const fixture = {title: "Dragon's Dogma 2: Dark Arisen", cover_img: cover, year: 2026, month: 10, day: 9,
  plats: [{key: 'steam', name: 'Steam', img: 'https://example.test/ultrawide-package.jpg'}]};
assert(context.card(fixture).innerHTML.includes('class="cover" src="' + cover + '"'));
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
console.log('Game cover valid: priority source, suitable JPEG ratio and unchanged wide-banner fallback');
