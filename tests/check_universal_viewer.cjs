// Universal viewer template: inline script syntax, required controls and camera math.
// No browser, WebGL or network needed.
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');

const raw = fs.readFileSync(path.join(__dirname, '..', 'universal_viewer_template.html'), 'utf8');
const scripts = [...raw.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const inline = scripts.at(-1);
new vm.Script(inline, {filename: 'universal_viewer_inline.js'});
// Older iOS Safari compatibility: no optional chaining / nullish coalescing / regex lookbehind.
assert.ok(!/\?\.[a-zA-Z_$[(]/.test(inline), 'optional chaining is not supported by older Safari');
assert.ok(!/\?\?/.test(inline), 'nullish coalescing is not supported by older Safari');
assert.ok(!/\(\?<[=!]/.test(inline), 'regex lookbehind is not supported by older Safari');
assert.ok(!/https?:\/\//.test(inline), 'the viewer must not depend on the network');

for (const id of ['plot', 'sheet', 'dock', 'search', 'items', 'meshes', 'lines', 'contours', 'entrances',
  'zoomIn', 'zoomOut', 'joyPad', 'selection', 'solo', 'savePng', 'resetTop', 'loading', 'model-json']) {
  assert.ok(raw.includes(`id="${id}"`), 'missing element #' + id);
}
for (const tab of ['browse', 'layers', 'view', 'info']) {
  assert.ok(raw.includes(`data-tab="${tab}"`) && raw.includes(`data-pane="${tab}"`), 'missing tab ' + tab);
}
for (const layout of ['landscape', 'wide']) assert.ok(raw.includes(`[data-layout=${layout}]`), 'missing layout ' + layout);
assert.ok(raw.includes('viewport-fit=cover') && raw.includes('safe-area-inset-bottom'), 'iPhone safe areas');
assert.ok(raw.includes('(any-pointer: coarse)') && raw.includes('(any-pointer: fine)'), 'input detection');
assert.ok(raw.includes("'gesturestart'"), 'Safari gesture events must not zoom the page');
console.log('Universal viewer syntax, controls and compatibility: OK');

const math = raw.match(/\/\/ CAMERA_MATH_START[^\n]*\n([\s\S]+?)\/\/ CAMERA_MATH_END/);
assert.ok(math, 'camera helpers not found');
const lib = vm.runInNewContext(math[1] + '\n({zoomCamera, panCamera, cameraDistance, visibleHeight});', {});
const cam = {eye: {x: 1.4, y: -1.3, z: 1.1}, up: {x: 0, y: 0, z: 1}, center: {x: 0.12, y: -0.21, z: 0.3}};
const frozen = JSON.stringify(cam);
const sub = (a, b) => ({x: a.x - b.x, y: a.y - b.y, z: a.z - b.z});
const norm = v => Math.hypot(v.x, v.y, v.z);
const near = (a, b, eps = 1e-12) => norm(sub(a, b)) < eps;

// Zoom: like Plotly's wheel, scale eye-center about the (possibly panned) center.
const zin = lib.zoomCamera(cam, 0.5);
assert.ok(near(zin.center, cam.center), 'zoom moved the center');
assert.ok(Math.abs(lib.cameraDistance(zin) - lib.cameraDistance(cam) * 0.5) < 1e-12, 'zoom factor');
const dir = v => { const n = norm(v); return {x: v.x / n, y: v.y / n, z: v.z / n}; };
assert.ok(near(dir(sub(zin.eye, zin.center)), dir(sub(cam.eye, cam.center))), 'zoom rotated the view');
assert.ok(Math.abs(lib.cameraDistance(lib.zoomCamera(zin, 2)) - lib.cameraDistance(cam)) < 1e-12, 'zoom roundtrip');
assert.ok(lib.cameraDistance(lib.zoomCamera(cam, 1e-9)) >= 0.04 - 1e-12, 'minimum distance');
assert.ok(lib.cameraDistance(lib.zoomCamera(cam, 1e9)) <= 40 + 1e-9, 'maximum distance');

// Pan: like Plotly's right-drag, eye and center translate together (no rotation, no zoom).
const right = lib.panCamera(cam, 0.5, 0), left = lib.panCamera(cam, -0.5, 0);
const up = lib.panCamera(cam, 0, -0.5), down = lib.panCamera(cam, 0, 0.5);
for (const c of [right, left, up, down]) {
  assert.ok(near(sub(c.eye, c.center), sub(cam.eye, cam.center)), 'pan rotated or zoomed the view');
  assert.ok(Math.abs(norm(sub(c.center, cam.center)) - 0.5) < 1e-12, 'pan distance');
}
const r = sub(right.center, cam.center), u = sub(up.center, cam.center);
const view = sub(cam.center, cam.eye);
assert.ok(Math.abs(r.x * u.x + r.y * u.y + r.z * u.z) < 1e-12, 'pan axes not orthogonal');
assert.ok(Math.abs(r.x * view.x + r.y * view.y + r.z * view.z) < 1e-12, 'pan moves along the view direction');
assert.ok(near(lib.panCamera(right, -0.5, 0).center, cam.center), 'pan not reversible');
assert.ok(near(sub(left.center, cam.center), {x: -r.x, y: -r.y, z: -r.z}), 'left/right not symmetric');
assert.equal(JSON.stringify(cam), frozen, 'input camera mutated');
// Model moves right on screen => camera moves left: with the default view (looking +x+y), screen right ~ +x-ish.
const top = {eye: {x: 0, y: 0, z: 2.6}, up: {x: 0, y: 1, z: 0}, center: {x: 0, y: 0, z: 0}};
const topRight = lib.panCamera(top, 1, 0);
assert.ok(topRight.center.x < -0.99 && Math.abs(topRight.center.y) < 1e-12, 'plan view: model right means camera west');
const topDown = lib.panCamera(top, 0, 1);
assert.ok(topDown.center.y > 0.99, 'plan view: model down means camera north');
assert.ok(lib.visibleHeight(cam) > 0, 'visible height');
console.log('Universal viewer zoom/pan camera math: OK');
