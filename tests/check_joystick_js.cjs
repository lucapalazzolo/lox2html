// Standalone camera/joystick regression: no WebGL and no external dependencies.
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const assert=require('node:assert/strict');
const raw=fs.readFileSync(path.join(__dirname,'..','mobile_viewer_template.html'),'utf8');
assert.ok(raw.includes('id="joyPad"')&&raw.includes('id="joyThumb"'),'Joystick elements missing');
assert.ok(raw.includes('.joyPad{')&&raw.includes('touch-action:none'),'Joystick must capture the touch gesture');
assert.ok(raw.includes("addEventListener('pointerdown'")&&raw.includes("addEventListener('pointerup'"),'Pointer events missing');
assert.ok(raw.includes("addEventListener('touchmove'")&&raw.includes('Older WebKit'),'Touch events fallback missing');
const match=raw.match(/\/\/ JOYSTICK_MATH_START[^\n]*\n([\s\S]+?)\/\/ JOYSTICK_MATH_END/);
assert.ok(match,'Math helper not found');
const pan=vm.runInNewContext(match[1]+'\npanCamera;',{});
const camera={eye:{x:1.4,y:-1.3,z:1.1},up:{x:0,y:0,z:1},center:{x:.12,y:-.21,z:.3}};
const clone=JSON.stringify(camera);
const vec=(a,b)=>({x:b.x-a.x,y:b.y-a.y,z:b.z-a.z});
const dot=(a,b)=>a.x*b.x+a.y*b.y+a.z*b.z;
const norm=a=>Math.hypot(a.x,a.y,a.z);
const zero=pan(camera,0,0);
assert.ok(norm(vec(camera.center,zero.center))<1e-14,'Neutral joystick moves camera');
const right=pan(camera,.5,0),left=pan(camera,-.5,0),up=pan(camera,0,-.5),down=pan(camera,0,.5);
assert.equal(JSON.stringify(camera),clone,'The input camera was changed');
for(const c of [right,left,up,down]){
 assert.equal(JSON.stringify(c.eye),JSON.stringify(camera.eye),'Joystick changes zoom or rotation (eye)');
 assert.equal(JSON.stringify(c.up),JSON.stringify(camera.up),'Joystick changes rotation (up)');
 assert.ok(Math.abs(norm(vec(camera.center,c.center))-.5)<1e-12,'Joystick movement must be uniform');
}
const r=vec(camera.center,right.center),l=vec(camera.center,left.center);
const u=vec(camera.center,up.center),d=vec(camera.center,down.center);
assert.ok(norm({x:r.x+l.x,y:r.y+l.y,z:r.z+l.z})<1e-12,'Left and right do not cancel');
assert.ok(norm({x:u.x+d.x,y:u.y+d.y,z:u.z+d.z})<1e-12,'Up and down do not cancel');
assert.ok(Math.abs(dot(r,u))<1e-12,'Screen plane basis is not orthogonal');
const back=pan(right,-.5,0);
assert.ok(norm(vec(camera.center,back.center))<1e-12,'Joystick pan not reversible');
const top={eye:{x:0,y:0,z:2.65},up:{x:0,y:1,z:0},center:{x:0,y:0,z:0}};
const side={eye:{x:0,y:-2.65,z:.02},up:{x:0,y:0,z:1},center:{x:0,y:0,z:0}};
for(const view of [top,side]){
 const t=pan(view,.4,.5);
 assert.ok(Number.isFinite(t.center.x)&&Number.isFinite(t.center.y)&&Number.isFinite(t.center.z),'View-mode pan invalid');
 assert.deepEqual({...t.eye},{...view.eye});
}
assert.ok(raw.includes('requestAnimationFrame(joyTick)'),'Continuous joystick loop absent');
assert.ok(raw.includes('joyBusy'),'Renderer rate limiting absent');
assert.ok(raw.includes("window.addEventListener('blur',joyRelease)"),'App switch stop absent');
console.log('Camera pan invariants / joystick controls: OK');
