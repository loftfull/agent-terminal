/* Journal observations, never inferred live agents or model identities. */
function studioPanel(root){
 const box=el('section',undefined,'studio');box.setAttribute('aria-label','Студия проекта');
 const head=el('div',undefined,'studio-head'),orb=el('div',undefined,'studio-orb');orb.setAttribute('aria-hidden','true');append(orb,el('span',undefined,'orbit ld ld-spin'),el('span','◈','ld ld-breath'));
 const intro=el('div');append(intro,el('div','ИСПОЛНИТЕЛИ И СВИДЕТЕЛЬСТВА','eyebrow'),el('h2','Последние запуски','studio-title'),el('p',state.mode==='snapshot'?'Сохранённый снимок · непрерывная связь с агентами не подключена':'Чтение журнала · непрерывная связь с агентами не подключена','studio-note'));append(head,orb,intro);box.append(head);
 const controls=el('div',undefined,'studio-controls'),pause=el('button',document.body.classList.contains('motion-paused')?'Включить движение':'Остановить движение');pause.setAttribute('aria-pressed',String(document.body.classList.contains('motion-paused')));pause.onclick=()=>{const stopped=document.body.classList.toggle('motion-paused');if(stopped)document.getAnimations().filter(a=>a.effect?.target===$('content')).forEach(a=>a.cancel());pause.textContent=stopped?'Включить движение':'Остановить движение';pause.setAttribute('aria-pressed',String(stopped))};controls.append(pause);
 const versions=el('button','Версии и снимки');versions.onclick=()=>chooseTab('releases');controls.append(versions);box.append(controls);
 box.append(el('p','Кольцо движется только при загрузке данных. Ниже — последние сохранённые запуски, а не список работающих сейчас моделей.','studio-note'));
 const grid=el('div',undefined,'studio-run-grid');const runs=arr(state.runs).slice().reverse().slice(0,3);
 const names={succeeded:'Команда завершилась',failed:'Команда завершилась с ошибкой',running:'Зарегистрирован запуск · активность неизвестна',starting:'Зарегистрирован старт',timed_out:'Превышено время',interrupted:'Прервано',launch_error:'Ошибка запуска',supervisor_error:'Ошибка контроля'};
 if(!runs.length)grid.append(el('p','Запуски пока не зарегистрированы. Модели и агенты не определены.','meta'));
 runs.forEach(r=>{const n=el('article',undefined,'studio-run');append(n,el('span',r.status==='succeeded'?'✓':r.status==='failed'?'!':'◇','studio-icon'),el('h3',arr(state.tasks).find(t=>t.task_id===r.task_id)?.title||r.task_id||'Запуск без имени'),badge(names[r.status]||'Состояние неизвестно',r.status==='succeeded'?'good':'warn'),el('p',r.model_id&&r.model_id!=='unknown'?'Модель (сообщена): '+r.model_id:'Модель не указана','meta'),el('p','Последнее событие: '+(r.ended_at||r.started_at||'дата неизвестна'),'meta'));const d=disclosure('studio:'+r.run_id,'Открыть свидетельство');d.append(el('pre',JSON.stringify({run_id:r.run_id,event_id:r.event_id,session_id:r.session_id,exit_code:r.exit_code,argv:r.argv},null,2),'code'));n.append(d);grid.append(n)});box.append(grid);runExplorer(box);root.append(box);
}

// Session-oriented inspection inspired by Langfuse's observation model.
// Existing records only: no inferred activity, cost, tokens or parent spans.
let runQuery='',runStatus='all',runModel='all',runLimit=20;
function selectRuns(runs,{query='',status='all',model='all'}={}){
 const needle=query.trim().toLocaleLowerCase('ru');
 return runs.slice().reverse().filter(r=>(status==='all'||r.status===status)&&(model==='all'||(r.model_id||'unknown')===model)&&(!needle||[r.run_id,r.task_id,r.session_id,r.model_id].join(' ').toLocaleLowerCase('ru').includes(needle)));
}
function runDuration(run){
 if(!run.started_at||!run.ended_at)return 'Длительность неизвестна';
 const elapsed=Date.parse(run.ended_at)-Date.parse(run.started_at);
 return Number.isFinite(elapsed)&&elapsed>=0?(elapsed/1000).toFixed(1)+' с':'Длительность неизвестна';
}
function runExplorer(root){
 const all=arr(state.runs),box=disclosure('run-explorer','Все запуски · '+all.length);box.id='run-explorer';
 box.append(el('p','Фильтры используют только сохранённые данные. Статус «запуск» не подтверждает текущую активность.','meta'));
 const controls=el('div',undefined,'run-filters'),search=el('input',undefined,'search');search.id='run-query';search.type='search';search.placeholder='ID сессии, задачи, запуска или модель';search.setAttribute('aria-label','Поиск запусков');search.value=runQuery;
 const status=el('select'),model=el('select');status.setAttribute('aria-label','Статус запуска');model.setAttribute('aria-label','Модель запуска');
 const names={succeeded:'Успешный выход',failed:'Ошибка',starting:'Старт зарегистрирован',running:'Запуск зарегистрирован',timed_out:'Лимит времени',interrupted:'Прервано',launch_error:'Ошибка запуска',supervisor_error:'Ошибка контроля'};
 [['all','Все статусы'],...Array.from(new Set(all.map(r=>r.status))).map(v=>[v,names[v]||v])].forEach(([v,t])=>{const o=el('option',t);o.value=v;status.append(o)});
 [['all','Все модели'],...Array.from(new Set(all.map(r=>r.model_id||'unknown'))).map(v=>[v,v==='unknown'?'Модель не указана':v])].forEach(([v,t])=>{const o=el('option',t);o.value=v;model.append(o)});
 if(!Array.from(status.options).some(o=>o.value===runStatus))runStatus='all';if(!Array.from(model.options).some(o=>o.value===runModel))runModel='all';status.value=runStatus;model.value=runModel;
 append(controls,search,status,model);box.append(controls);const output=el('div');box.append(output);
 function fill(){output.replaceChildren();const rows=selectRuns(all,{query:runQuery,status:runStatus,model:runModel});output.append(el('p','Найдено '+rows.length+' из '+all.length+' · показано '+Math.min(runLimit,rows.length),'meta'));if(!rows.length)empty(output,'Нет запусков по выбранным условиям.');rows.slice(0,runLimit).forEach(r=>{const item=el('article',undefined,'item');append(item,el('h3',arr(state.tasks).find(t=>t.task_id===r.task_id)?.title||r.task_id||r.run_id),el('p',(names[r.status]||r.status)+' · '+runDuration(r)),el('p','Модель (сообщена): '+(r.model_id||'unknown')+' · Сессия: '+(r.session_id||'не указана'),'meta'));const detail=disclosure('explorer:'+r.run_id,'Результат и источник');detail.append(el('pre',JSON.stringify({run_id:r.run_id,event_id:r.event_id,started_at:r.started_at,ended_at:r.ended_at,exit_code:r.exit_code,argv:r.argv,stdout:r.stdout,stderr:r.stderr},null,2),'connection-data'));item.append(detail);output.append(item)});if(rows.length>runLimit){const more=el('button','Показать ещё 20');more.onclick=()=>{runLimit+=20;fill()};output.append(more)}}
 search.oninput=()=>{runQuery=search.value;runLimit=20;fill()};status.onchange=()=>{runStatus=status.value;runLimit=20;fill()};model.onchange=()=>{runModel=model.value;runLimit=20;fill()};fill();root.append(box);
}
if(typeof module!=='undefined')module.exports={selectRuns,runDuration};
