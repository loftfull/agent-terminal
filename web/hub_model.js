/* Pure projections; missing evidence never becomes acceptance or live activity. */
const TerminalHub=(()=>{
 const list=v=>Array.isArray(v)?v:[];
 const routes=[['overview','Панорама','layers'],['plans','План','workflow'],['agents','Исполнители','bot'],['releases','Версии','git-branch'],['handoff','Контекст','arrow-right'],['connections','Подключения','plug'],['tasks','Задачи'],['audits','Проверки'],['messages','Сообщения'],['favorites','Избранное'],['history','История'],['components','Компоненты'],['locations','Расположения'],['visuals','Визуальные материалы']];
 function overview(s){const tasks=list(s.tasks),runs=list(s.runs);return {
  next:s.focus?.next_step||s.handoff?.next_step||'Следующий шаг ещё не выбран',
  needsReview:tasks.filter(t=>['review','needs_review'].includes(t.status)).length,
  blocked:tasks.slice().reverse().filter(t=>['blocked','needs_input'].includes(t.status)).length,
  latest:list(s.checkpoints)[0]||null,
  stages:[{title:'Замысел',detail:s.project?.goal?'Цель записана':'Нет цели',route:'handoff'},
   {title:'План',detail:list(s.plans).length+' планов',route:'plans'},
   {title:'Реализация',detail:runs.length+' записей запусков',route:'agents'},
   {title:'Проверка',detail:tasks.filter(t=>['review','needs_review'].includes(t.status)).length+' задач на проверке',route:'audits'},
   {title:'Версия',detail:list(s.checkpoints).length+' контрольных точек',route:'releases'}]};}
 function signature(s){const {observed_at,mode,...content}=s;return JSON.stringify(content)}
 function context(s,{full=false,taskId=null}={}){
  if(full)return {data:s,omissions:[],chars:JSON.stringify(s,null,2).length};
  const tasks=list(s.tasks);if(taskId&&!tasks.some(t=>t.task_id===taskId))throw Error('Задача отсутствует в выбранном проекте');
  const selected=taskId?tasks.filter(t=>t.task_id===taskId):tasks.slice().reverse().filter(t=>['blocked','review','needs_review','needs_input','running'].includes(t.status)).slice(0,5);
  const ids=new Set(selected.flatMap(t=>list(t.evidence_event_ids)));
  const allEvents=list(s.events);let changed=true;while(changed){changed=false;for(const e of allEvents){const refs=Array.isArray(e.supersedes)?e.supersedes:typeof e.supersedes==='string'?[e.supersedes]:[];if(ids.has(e.event_id)||refs.some(id=>ids.has(id))){for(const id of [e.event_id,...refs])if(id&&!ids.has(id)){ids.add(id);changed=true}}}}const events=allEvents.filter(e=>ids.has(e.event_id));const sourceIds=new Set([...events.flatMap(e=>list(e.source_ids)),...selected.flatMap(t=>list(t.source_ids))]);
  const data={schema:'terminal-context-pack/v1',project:s.project,journal_tip:s.integrity?.journal_tip||null,observed_at:s.observed_at,mode:s.mode,
   constraints:s.constraints||s.project?.constraints||[],task_guards:tasks.map(t=>({task_id:t.task_id,constraints:t.constraints||[],stop_conditions:t.stop_conditions||[],acceptance:t.acceptance||[]})),decisions:s.decisions||[],handoff:s.handoff,conflicts:s.conflicts,search_queue:s.search_queue,
   code_checkpoints:list(s.checkpoints).map(v=>({name:v.name,commit_sha:v.commit_sha,occurred_at:v.occurred_at,evidence_event_ids:v.evidence_event_ids})),locations:s.locations||[],development_lines:s.development_lines||s.lines||[],selected_task_ids:selected.map(t=>t.task_id),tasks:selected,events,sources:list(s.sources).filter(x=>sourceIds.has(x.source_id)),
   missing_event_ids:[...ids].filter(id=>!events.some(e=>e.event_id===id)),
   coverage:{complete:false,total_tasks:tasks.length,total_events:list(s.events).length,included_events:events.length,full_archive:'Отдельный полный JSON; краткий пакет не заменяет архив'}};
  return {data,omissions:['История вне выбранных задач','Исходники и недоступные чаты','Полные версии, запуски и материалы: в полном JSON'],chars:JSON.stringify(data,null,2).length};
 }
 return {routes,overview,context,signature};
})();
if(typeof module!=='undefined')module.exports=TerminalHub;
