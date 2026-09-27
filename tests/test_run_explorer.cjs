const assert=require('node:assert/strict');
const {selectRuns,runDuration}=require('../web/studio.js');
const rows=[{run_id:'1',model_id:'Claude',session_id:'s1',status:'failed'},{run_id:'2',model_id:'Codex',session_id:'s2',status:'succeeded'},{run_id:'3',status:'running'}];
assert.deepEqual(selectRuns(rows,{status:'failed',model:'Claude',query:'S1'}).map(r=>r.run_id),['1']);
assert.equal(selectRuns(rows,{model:'unknown'}).length,1);assert.equal(selectRuns(rows,{query:'missing'}).length,0);assert.equal(rows[0].run_id,'1');
assert.equal(runDuration({started_at:'2026-09-27T00:00:00Z',ended_at:'2026-09-27T00:00:02Z'}),'2.0 с');
for(const r of [{},{started_at:'bad',ended_at:'bad'},{started_at:'2026-09-28',ended_at:'2026-09-27'}])assert.equal(runDuration(r),'Длительность неизвестна');
console.log('PASS: combined run filters, unknown model, immutable input, measured duration only');
