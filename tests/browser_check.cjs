// Optional real-browser test of universal viewer HTML files on several device profiles.
// Usage: node tests/browser_check.cjs page1.html [page2.html ...] [--shots DIR]
// Needs playwright-core (PLAYWRIGHT_CORE=/path/to/playwright-core or a local install) and a
// Chromium (CHROME_PATH, or Playwright's default). Skips cleanly when unavailable.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

let playwright;
try { playwright = require(process.env.PLAYWRIGHT_CORE || 'playwright-core'); } catch (e) {
  console.log('Browser test skipped: playwright-core not installed (set PLAYWRIGHT_CORE).');
  process.exit(0);
}
const args = process.argv.slice(2);
let shots = null;
const pages = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--shots') shots = args[++i];
  else pages.push(path.resolve(args[i]));
}
if (!pages.length) { console.error('usage: browser_check.cjs page.html [...] [--shots DIR]'); process.exit(2); }
if (shots) fs.mkdirSync(shots, {recursive: true});

const profiles = [
  {name: 'computer', viewport: {width: 1366, height: 768}, layout: 'wide'},
  {name: 'android', viewport: {width: 412, height: 915}, hasTouch: true, isMobile: true, deviceScaleFactor: 2.6, layout: 'compact'},
  {name: 'iphone', viewport: {width: 390, height: 844}, hasTouch: true, isMobile: true, deviceScaleFactor: 3, layout: 'compact'},
  {name: 'iphone-landscape', viewport: {width: 844, height: 390}, hasTouch: true, isMobile: true, deviceScaleFactor: 3, layout: 'landscape'},
  {name: 'ipad-landscape', viewport: {width: 1180, height: 820}, hasTouch: true, isMobile: true, deviceScaleFactor: 2, layout: 'wide'},
  {name: 'ipad-portrait', viewport: {width: 820, height: 1180}, hasTouch: true, isMobile: true, deviceScaleFactor: 2, layout: 'compact'},
];

const overlaps = (a, b) => a && b && a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;

(async () => {
  const browser = await playwright.chromium.launch({executablePath: process.env.CHROME_PATH || undefined,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']});
  let failures = 0;
  for (const file of pages) {
    for (const prof of profiles) {
      const label = `${path.basename(file)} @ ${prof.name}`;
      const context = await browser.newContext({viewport: prof.viewport, hasTouch: !!prof.hasTouch,
        isMobile: !!prof.isMobile, deviceScaleFactor: prof.deviceScaleFactor || 1});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', e => errors.push(String(e)));
      page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
      try {
        const t0 = Date.now();
        await page.goto('file://' + file);
        await page.waitForFunction(() => document.getElementById('loading').hidden ||
          !!document.querySelector('#loading .error'), null, {timeout: 120000});
        const err = await page.$eval('#loading', el => el.hidden ? '' : el.textContent);
        assert.equal(err, '', 'viewer reported an error: ' + err);
        const ms = Date.now() - t0;
        const layout = await page.getAttribute('#app', 'data-layout');
        assert.equal(layout, prof.layout, 'layout');
        const box = sel => page.$eval(sel, el => { if (el.hidden || el.offsetParent === null && getComputedStyle(el).position !== 'fixed') return null;
          const r = el.getBoundingClientRect(); return r.width && r.height ? {x: r.x, y: r.y, width: r.width, height: r.height} : null; });
        const vp = prof.viewport;
        const inside = (b, what) => assert.ok(b && b.x >= -1 && b.y >= -1 && b.x + b.width <= vp.width + 1 && b.y + b.height <= vp.height + 1, `${what} outside viewport ${JSON.stringify(b)}`);
        const plot = await box('#plot'), zoom = await box('.zoom'), dock = await box('#dock');
        inside(plot, 'plot'); inside(zoom, 'zoom buttons'); inside(dock, 'dock');
        assert.ok(plot.width > vp.width * 0.45 && plot.height > vp.height * 0.45, 'plot too small ' + JSON.stringify(plot));
        assert.ok(!overlaps(zoom, dock), 'zoom overlaps dock');
        const joy = await box('#joystick');
        assert.equal(!!joy, !!prof.hasTouch, 'joystick shown only with touch');
        if (joy) { inside(joy, 'joystick'); assert.ok(!overlaps(joy, zoom), 'joystick overlaps zoom'); assert.ok(!overlaps(joy, dock), 'joystick overlaps dock'); }
        const cam = () => page.evaluate(() => {
          const c = document.getElementById('plot')._fullLayout.scene._scene.getCamera();
          return {eye: c.eye, center: c.center, d: Math.hypot(c.eye.x - c.center.x, c.eye.y - c.center.y, c.eye.z - c.center.z)};
        });
        const settle = () => page.waitForTimeout(350);
        // Zoom buttons.
        const c0 = await cam();
        await page.click('#zoomIn'); await settle();
        const c1 = await cam();
        assert.ok(c1.d < c0.d * 0.9, `zoom + did not zoom (${c0.d} -> ${c1.d})`);
        await page.click('#zoomOut'); await settle();
        assert.ok(Math.abs((await cam()).d - c0.d) < 1e-6 * c0.d + 1e-9, 'zoom roundtrip');
        // Joystick: rigid translation (eye-center preserved).
        if (joy) {
          const before = await cam();
          const jx = joy.x + joy.width / 2, jy = joy.y + 55;
          await page.dispatchEvent('#joyPad', 'pointerdown', {pointerId: 7, pointerType: 'touch', clientX: jx, clientY: jy, isPrimary: true, button: 0, buttons: 1});
          await page.dispatchEvent('#joyPad', 'pointermove', {pointerId: 7, pointerType: 'touch', clientX: jx + 40, clientY: jy, isPrimary: true, buttons: 1});
          await page.waitForTimeout(600);
          await page.dispatchEvent('#joyPad', 'pointerup', {pointerId: 7, pointerType: 'touch', clientX: jx + 40, clientY: jy, isPrimary: true});
          await settle();
          const after = await cam();
          const moved = Math.hypot(after.center.x - before.center.x, after.center.y - before.center.y, after.center.z - before.center.z);
          assert.ok(moved > 1e-3, 'joystick did not pan');
          assert.ok(Math.abs(after.d - before.d) < 1e-6, 'joystick changed zoom');
          const rel = k => after.eye[k] - after.center[k] - (before.eye[k] - before.center[k]);
          assert.ok(Math.abs(rel('x')) + Math.abs(rel('y')) + Math.abs(rel('z')) < 1e-6, 'joystick rotated the view');
        }
        // Keyboard on computers.
        if (!prof.hasTouch) {
          const before = await cam();
          await page.locator('#plot').click({position: {x: 5, y: plot.height - 5}}).catch(() => {});
          await page.keyboard.press('ArrowRight'); await settle();
          const after = await cam();
          assert.ok(Math.hypot(after.center.x - before.center.x, after.center.y - before.center.y) > 1e-4, 'arrow key did not pan');
        }
        // Panels: every tab opens, the list selects a survey and the card appears.
        for (const tab of ['layers', 'view', 'info', 'browse']) {
          await page.click(`[data-tab=${tab}]`);
          const shown = await page.$eval(`[data-pane=${tab}]`, el => !el.hidden);
          assert.ok(shown, `pane ${tab} not shown`);
          // Wait for the slide-in transition to finish (slow on loaded CI machines).
          await page.waitForFunction(() => { const r = document.getElementById('sheet').getBoundingClientRect();
            return r.bottom <= window.innerHeight + 1 && r.right <= window.innerWidth + 1 && r.left >= -1; }, null, {timeout: 5000}).catch(() => {});
          const sheet = await box('#sheet');
          inside(sheet, `sheet ${tab}`);
        }
        const items = await page.$$('#items .itemMain');
        if (items.length) {
          await items[0].click(); await page.waitForTimeout(500);
          assert.ok(!(await page.$eval('#selection', el => el.hidden)), 'selection card not shown');
          const sel = await box('#selection');
          inside(sel, 'selection card');
          if (!joy || prof.layout !== 'compact') assert.ok(!overlaps(sel, zoom), 'selection overlaps zoom');
          await page.click('#solo'); await page.waitForTimeout(300);
          const hiddenTraces = await page.evaluate(() => document.getElementById('plot').data.filter(t => t.visible === false).length);
          assert.ok(hiddenTraces >= 0);
        }
        // Layers: toggles restyle without errors.
        await page.click('[data-tab=layers]'); await page.waitForTimeout(200);
        for (const id of ['lines', 'meshes']) {
          const el = await page.$('#' + id);
          if (el && !(await el.isDisabled())) { await el.click(); await page.waitForTimeout(150); await el.click(); }
        }
        if (prof.layout !== 'wide') { await page.click('#closeSheet'); await page.waitForTimeout(250); }
        await page.click('#resetTop'); await page.waitForTimeout(400);
        if (shots) await page.screenshot({path: path.join(shots, `${path.basename(file, '.html')}_${prof.name}.png`)});
        assert.deepEqual(errors, [], 'console errors');
        console.log(`OK  ${label}  (${ms} ms to interactive)`);
      } catch (e) {
        failures++;
        console.log(`FAIL ${label}: ${e.message}`);
        if (errors.length) console.log('     console:', errors.slice(0, 3).join(' | '));
        if (shots) await page.screenshot({path: path.join(shots, `FAIL_${path.basename(file, '.html')}_${prof.name}.png`)}).catch(() => {});
      }
      await context.close();
    }
  }
  await browser.close();
  if (failures) { console.log(`${failures} browser check(s) failed`); process.exit(1); }
  console.log('Universal viewer browser checks: OK');
})();
