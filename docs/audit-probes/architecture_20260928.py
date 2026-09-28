import tempfile,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from project_history_agent import empty_state
from project_history_journal import bootstrap_journal_from_state,verify_journal_set
from runtime_journal import append_mutation_batch
from project_history_mcp import HistoryReader
from terminal_dashboard import build_view
from terminal_context import read_layer

def fresh(d):
 p=Path(d);bootstrap_journal_from_state(empty_state('p','Project',''),p/'PROJECT_HISTORY.events.jsonl');return p
with tempfile.TemporaryDirectory() as d:
 p=fresh(d)
 append_mutation_batch(p,[('event.add',{'event_id':'EV-BAD','event_type':'terminal_contract','summary':'Imported contract without payload','evidence_status':'reported','source_ids':[]})])
 print('malformed_reserved_event', 'chain_valid',verify_journal_set(p)['ok'], 'reader_events',len(HistoryReader(p,'p').read()[0]['events']))
 try:build_view(p,'p')
 except Exception as e:print('dashboard_error',type(e).__name__,str(e))
with tempfile.TemporaryDirectory() as d:
 p=fresh(d)
 append_mutation_batch(p,[('event.add',{'event_id':'old','summary':'Use SQLite','evidence_status':'requested'}),('event.add',{'event_id':'new','summary':'Use JSONL','supersedes':['old'],'evidence_status':'requested'})])
 l1=read_layer(p,'p','L1');l2=read_layer(p,'p','L2')
 print('supersedes_l1',l1['items'][-1].get('supersedes'),'supersedes_l2',l2['items'][-1].get('supersedes'))
 # Both concurrent callers read the same base; low-level writer has no expected tip.
 tip=verify_journal_set(p)['last_hash']
 append_mutation_batch(p,[('handoff.patch',{'next_step':'Writer A'})])
 append_mutation_batch(p,[('handoff.patch',{'next_step':'Writer B from stale '+tip})])
 print('stale_patch_last_writer_wins',HistoryReader(p,'p').read()[0]['handoff']['next_step'])
with tempfile.TemporaryDirectory() as d:
 p=fresh(d)
 common={'event_type':'decision','summary':'Use SQLite','occurred_at':'2026-09-28T10:00:00Z','source_ids':[]}
 records=append_mutation_batch(p,[('event.add',dict(common,event_id='EV-REPORTED',evidence_status='reported')),('event.add',dict(common,event_id='EV-VERIFIED',evidence_status='verified',supersedes=['EV-REPORTED']))])
 events=HistoryReader(p,'p').read()[0]['events']
 print('dedupe_collision',json.dumps({'written_mutations':len(records),'replayed_events':len(events),'retained_ids':[e['event_id'] for e in events],'retained_classes':[e['evidence_status'] for e in events]}))
import asyncio
from project_history_mcp import create_server
async def mcp_probe():
 with tempfile.TemporaryDirectory() as d:
  p=fresh(d)
  append_mutation_batch(p,[('event.add',{'event_id':'old','summary':'Use SQLite','evidence_status':'requested'}),('event.add',{'event_id':'new','summary':'Use JSONL','supersedes':['old'],'evidence_status':'requested'})])
  server=create_server(p,'p')
  result=await server.call_tool('read_context_layer',{'level':'L1'})
  print('mcp_registered_L1',result.model_dump()['structured_content']['items'])
asyncio.run(mcp_probe())
