/* Derived views only: missing evidence is never promoted to a resolved finding. */
const FixProgress = (() => {
 const rows=x=>Array.isArray(x)?x:[];
 function planGroup(s){return s==='implemented'?'component':s==='partial'||s==='component_implemented_host_acceptance_open'?'partial':s==='open'?'open':'unknown'}
 function derive(s){
  const plans={component:[],partial:[],open:[],unknown:[]};rows(s.plans).forEach(p=>plans[planGroup(p.status)].push(p));
  const events=rows(s.events), known=new Set(events.map(e=>e.event_id)), sources=new Set(rows(s.sources).map(e=>e.source_id)), findings=new Map();
  for(const e of events){const f=e.audit_finding;if(e.event_type!=='audit_finding_observation'||!f?.id)continue;
   const valid=rows(e.source_ids).length>0&&rows(e.source_ids).every(id=>sources.has(id))&&rows(f.evidence_event_ids).length>0&&rows(f.evidence_event_ids).every(id=>known.has(id));
   findings.set(f.id,{...f,status:valid?f.status:'unknown',event_id:e.event_id,source_ids:rows(e.source_ids)});
  }
  const days=new Map();let undated=0;
  for(const e of events){const stamp=e.occurred_at||e.observed_at;if(typeof stamp!=='string'||!/^\d{4}-\d{2}-\d{2}T/.test(stamp)||!Number.isFinite(Date.parse(stamp))){undated++;continue;}const d=new Date(stamp).toISOString().slice(0,10);if(!days.has(d))days.set(d,[]);days.get(d).push(e);}
  return {plans,findings:[...findings.values()],days:[...days].sort((a,b)=>a[0].localeCompare(b[0])),undated};
 }
 return {derive,planGroup};
})();
if(typeof module!=='undefined')module.exports=FixProgress;
