// Node syntax check for the inline mobile controller; Plotly bundle is excluded.
const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const root=path.resolve(__dirname,'..');
const raw=fs.readFileSync(path.join(root,'mobile_viewer_template.html'),'utf8');
const blocks=[...raw.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(x=>x[1]);
const inline=blocks.at(-1);
new vm.Script(inline,{filename:'mobile_viewer_inline.js'});
const required=['id="plot"','id="sheet"','id="meshes"','id="lines"','id="contours"','id="search"',
                'id="zoomIn"','id="zoomOut"','data-tab="browse"','data-tab="layers"','data-tab="view"'];
for(const s of required)if(!raw.includes(s))throw Error('Missing UI element: '+s);
if(/\.com\/(?:api|embed|assets)/.test(inline))throw Error('Unexpected network dependency');
console.log('Mobile UI JavaScript syntax and element checks: OK');

// Executable zoom-math regression (no WebGL or network needed).
const assert=require('node:assert/strict');
const match=raw.match(/\/\/ ZOOM_MATH_START[^\n]*\n([\s\S]+?)\/\/ ZOOM_MATH_END/);
assert.ok(match,'Zoom helper is absent');
const scale=vm.runInNewContext(match[1]+'\nscaledCamera;', {});
const start={eye:{x:1.5,y:-2.1,z:1},up:{x:0,y:0,z:1},center:{x:.1,y:0,z:0}};
const norm=c=>Math.hypot(c.eye.x,c.eye.y,c.eye.z);
const closer=scale(start,1/1.36),farther=scale(start,1.36);
assert.ok(norm(closer)<norm(start),'Zoom + must bring camera closer');
assert.ok(norm(farther)>norm(start),'Zoom - must move camera away');
assert.deepEqual(start.eye,{x:1.5,y:-2.1,z:1},'Zoom must not mutate input camera');
assert.ok(Math.abs(norm(scale(closer,1.36))-norm(start))<1e-10,'Zoom roundtrip');
assert.ok(norm(scale(start,1e-99))>=.16-1e-12,'Minimum zoom bound');
assert.ok(norm(scale(start,1e99))<=24+1e-12,'Maximum zoom bound');
assert.ok(raw.includes("P.addEventListener('touchmove'") && raw.includes('passive:false'),'Explicit Safari pinch is registered');
console.log('Mobile zoom +/- and pinch regression tests: OK');

const fZoom=raw.match(/function zoomBy\(factor\)\{[\s\S]*?\n\}/);
assert.ok(fZoom,'Zoom controller is absent');
const mockCamera={eye:{x:1.5,y:-2.1,z:1},up:{x:0,y:0,z:1},center:{x:0,y:0,z:0}};
const mockPlot={data:[{}],layout:{scene:{camera:mockCamera}}};
let relayoutCount=0;
const mockPlotly={relayout:(plot,update)=>{
  plot.layout.scene.camera=update['scene.camera'];relayoutCount++;
}};
const mock={P:mockPlot,Plotly:mockPlotly,camera:mockCamera,scaledCamera:scale};
vm.runInNewContext(fZoom[0]+'\nzoomBy(1/1.36); zoomBy(1.36);',mock);
assert.equal(relayoutCount,2,'Both zoom commands must apply Plotly camera changes');
assert.ok(Math.abs(norm(mockPlot.layout.scene.camera)-norm(mockCamera))<1e-10,'Camera roundtrip from controller');
console.log('Mobile zoom Plotly.relayout behavior: OK');
