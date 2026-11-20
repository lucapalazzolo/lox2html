const fs=require('fs'),vm=require('vm'),assert=require('assert');
const reference=__dirname+'/../esempi/DOSSENA_HTML_UNIVERSALE.html';
if(!fs.existsSync(reference)){console.log('Desktop viewer runtime test skipped: Dossena reference HTML not distributed.');process.exit(0);}
const html=fs.readFileSync(reference,'utf8');
const model=JSON.parse(html.match(/<script id="model-json" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const runtime=html.match(/<script>\s*(\(\(\)=>\{'use strict';[\s\S]*?)<\/script>/)[1];
class MockEl {
 constructor(id=''){this.id=id;this.textContent='';this.style={display:''};this.value='';this.checked=true;this.dataset={};this.listeners={};this.children=[];this.classList={toggle(){},add(){},remove(){}};}
 addEventListener(name,cb){this.listeners[name]=cb};append(...els){this.children.push(...els)}
 replaceChildren(...els){this.children=[...els]};querySelectorAll(sel){if(sel==='button')return [10,20,50].map(v=>{let e=new MockEl('button');e.dataset={val:String(v)};return e});return []}
 setAttribute(){};getAttribute(){};onclick(){};hasAttribute(){return false}
}
const elements={};const doc={getElementById(id){return elements[id]??(elements[id]=new MockEl(id));},
 createElement(tag){return new MockEl(tag)},activeElement:null};
elements['model-json']=new MockEl('model-json');elements['model-json'].textContent=JSON.stringify(model);
let plotted=[],restyled=0,relayouts=0;
const Plotly={newPlot:(el,traces,layout)=>{plotted=traces;el.on=()=>{};return Promise.resolve(el)},
 restyle:()=>{restyled++},relayout:()=>{relayouts++},downloadImage:()=>{},Plots:{resize:()=>{}}};
const window={devicePixelRatio:1,matchMedia:()=>({matches:false}),addEventListener(){}},document=doc;
vm.runInNewContext(runtime,{window,document,Plotly,console,Math,Number,Object,Array,String,JSON,setTimeout}, {timeout:2000});
setTimeout(()=>{
 assert.equal(model.meta.stats.shots,2320);assert.equal(model.groups.length,39);
 assert.equal(plotted.length,85); // 79 geometry + 4 contour + labels + catasto
 assert.equal(elements['countCaves'].textContent,32);assert.equal(elements['countMines'].textContent,7);
 assert.equal(elements['loading'].style.display,'none');
 elements['toggleMines'].listeners.change({target:{checked:false}});
 assert(restyled>0);
 elements['exag'].listeners.input({target:{value:'1.5'}});assert(relayouts>0);
 console.log('PASS: generic UI bootstrap, 85 traces, all 39 surveys, visibility and camera controls');
},10);
