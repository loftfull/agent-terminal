const assert=require('node:assert/strict');const C=require('../web/connections.js');
(async()=>{
 assert.equal(C.repository('https://github.com/loftfull/agent-terminal.git'),'loftfull/agent-terminal');
 for(const x of ['https://github.com.evil/a/b','https://token@github.com/a/b','https://github.com/a/b?token=x','https://github.com/a/b/tree/main','a/b/c','a/..'])assert.throws(()=>C.repository(x));
 const calls=[];const fetcher=async(url,options)=>{calls.push([url,options]);return {ok:!url.includes('/actions/'),status:403,json:async()=>url.endsWith('/a/b')?{full_name:'a/b',default_branch:'main'}:[]}};
 const data=await C.inspect('a/b',fetcher);assert.equal(calls.length,8);assert.equal(data.sections.actions.status,'unavailable');assert.equal(data.sections.readme.status,'observed');assert.equal(data.continuous_ingestion,false);assert(calls.every(([url,o])=>url.startsWith('https://api.github.com/repos/a/b')&&o.credentials==='omit'));
 const state={project:{project_id:'p',constraints:['A','B']},constraints:['TOP LEVEL RULE'],focus:{next_step:'NEXT'},events:[{text:'<script>untrusted</script>'}]};
 assert(!C.prompt(state).includes('<script>'));assert(C.prompt(state,{full:true}).includes('<script>'));assert(C.prompt(state,{existing:true}).includes('существующий чат'));assert(C.prompt(state).includes('"B"'));assert(C.prompt(state).includes('TOP LEVEL RULE'));assert(C.prompt(state).includes('NEXT'));
 const controller=new AbortController();controller.abort();await assert.rejects(()=>C.inspect('a/b',fetcher,controller.signal));
 console.log('PASS: repository validation, public-only requests, partial failures, cancellation, scoped short/full handoff');
})().catch(e=>{console.error(e);process.exitCode=1});
