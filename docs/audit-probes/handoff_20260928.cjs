const fs=require('node:fs');
const path=require('node:path').resolve(__dirname,'../..');
const H=require(path+'/web/hub_model.js');
const html=fs.readFileSync(path+'/docs/previews/Agent-Terminal-Studio.html','utf8');
const s=JSON.parse(html.match(/<script id=['"]initial-state['"] type=['"]application\/json['"]>([\s\S]*?)<\/script>/)[1]);
const results=s.tasks.map(t=>{
 const p=H.context(s,{taskId:t.task_id}).data;
 const ids=new Set(p.events.map(x=>x.event_id));
 const refs=[t.contract_event_id,t.report_event_id].filter(Boolean);
 return {task:t.task_id,missing:refs.filter(x=>!ids.has(x)),declared_missing:p.missing_event_ids,included_events:p.events.length};
});
console.log(JSON.stringify({tasks:s.tasks.length,affected:results.filter(x=>x.missing.length).length,results},null,2));
