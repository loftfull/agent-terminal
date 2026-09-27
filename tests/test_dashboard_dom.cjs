// DOM behavior only: jsdom does not validate layout or native modal focus trapping.
// npm install --prefix /tmp/terminal-dom-qa jsdom@26.1.0
// NODE_PATH=/tmp/terminal-dom-qa/node_modules node tests/test_dashboard_dom.cjs SNAPSHOT.html
const {JSDOM,VirtualConsole}=require('jsdom');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
const errors=[];const consoleSink=new VirtualConsole();consoleSink.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',url:'https://terminal.test/',virtualConsole:consoleSink,beforeParse(w){w.matchMedia=()=>({matches:true});w.Element.prototype.animate=()=>({});w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'))};}});
const d=dom.window.document;
assert.equal(dom.window.getComputedStyle(d.getElementById('github-connect')).backgroundColor,'rgb(23, 110, 112)','Primary action keeps its contrast background');
assert.equal(d.querySelectorAll('.tabs button').length,5);
assert.equal(d.querySelectorAll('.secondary-nav button').length,6);
for(const button of d.querySelectorAll('[data-tab]')){
 button.click();assert.equal(button.getAttribute('aria-current'),'page');
 assert.equal(d.querySelectorAll('[aria-current=page]').length,1);
 assert.equal(d.querySelector('#content').getAttribute('aria-label'),button.textContent);
 assert.equal(d.activeElement.id,'content');assert.ok(d.querySelector('#content').children.length,button.dataset.tab+' '+errors.join(';')); 
}
d.querySelector('[data-tab=overview]').click();
const runSearch=d.querySelector('#run-query');runSearch.value='NO_SUCH_RUN_928374';runSearch.dispatchEvent(new dom.window.Event('input'));assert.match(d.querySelector('#run-explorer').textContent,/Нет запусков/);runSearch.focus();d.querySelector('[data-tab=tasks]').click();assert.equal(d.querySelector('#content').getAttribute('aria-label'),'Задачи');assert.equal(d.querySelector('#run-explorer'),null);d.querySelector('[data-tab=overview]').click();
const first=d.querySelector('#content>section');assert.match(first.textContent,/Сейчас/);
const snapshot=JSON.parse(d.querySelector('#initial-state').textContent);
const next=snapshot.focus?.next_step||snapshot.handoff?.next_step;
assert.ok(first.textContent.includes(next));first.querySelector('button').click();
assert.ok(d.querySelector('#content>section').textContent.includes(next),'Next step survives overview toggle');
for(const id of ['chat-connect','github-connect']){
 const opener=d.getElementById(id);opener.focus();opener.click();const dialog=d.querySelector('dialog');assert.ok(dialog.open);
 if(id==='chat-connect'){assert.ok(dialog.querySelector('textarea').value.includes(next));const select=dialog.querySelector('select');select.value='existing';select.dispatchEvent(new dom.window.Event('change'));assert.match(dialog.querySelector('textarea').value,/существующий чат/)}
 dialog.querySelector('button').click();assert.equal(d.querySelector('dialog'),null);assert.equal(d.activeElement,opener);
}
const cache=require('../web/repository_cache.js'),{fixture}=require('./test_repository_cache.cjs');
cache.save(dom.window.localStorage,fixture('saved/repository'));
d.getElementById('github-connect').click();
let savedButton=[...d.querySelectorAll('dialog button')].find(b=>b.textContent.startsWith('saved/repository'));
assert.ok(savedButton);savedButton.click();assert.match(d.querySelector('dialog').textContent,/Сохранённый снимок, без обновления GitHub/);
[...d.querySelectorAll('dialog button')].find(b=>b.textContent==='Передать этот репозиторий в AI-чат').click();
assert.match(d.querySelector('dialog textarea').value,/saved\/repository/);assert.ok(!d.querySelector('dialog').textContent.includes('Постоянное чтение памяти через MCP'));
d.querySelector('dialog button').click();
const live=fixture('live/repository');dom.window.fetch=async url=>({ok:true,status:200,headers:{get:()=>null},json:async()=>{const name=new URL(url).pathname.split('/')[4];return name?live.sections[name].data:live.metadata}});
d.getElementById('github-connect').click();d.getElementById('repository-url').value='live/repository';d.querySelector('dialog form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));await new Promise(resolve=>setImmediate(resolve));
const saveButton=[...d.querySelectorAll('dialog button')].find(b=>b.textContent==='Сохранить снимок в браузере');assert.ok(saveButton);saveButton.click();assert.ok(cache.list(dom.window.localStorage).items.some(i=>i.repository==='live/repository'));d.querySelector('dialog button').click();
d.getElementById('github-connect').click();assert.ok([...d.querySelectorAll('dialog button')].some(b=>b.textContent.startsWith('live/repository')));d.querySelector('dialog button').click();
assert.deepEqual(errors,[]);dom.window.close();console.log('PASS: 11 sections, 5 primary actions, unique current state, panel focus, persistent next step, scoped handoff, modal close focus return (DOM only)');

})().catch(e=>{console.error(e);process.exitCode=1});
