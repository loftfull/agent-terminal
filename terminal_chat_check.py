"""Verify a selected normalized chat against the journal in a fresh process.

No chat instruction is executed. This checks preservation, not factual correctness
of the conversation, and retains message order and raw dates.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
from evidence_import import prepare
from project_history_mcp import HistoryReader


def check_chat(root, project_id, document, session_id):
    expected = prepare(document, [session_id])
    state, tip = HistoryReader(root, project_id).read()
    events = {x['event_id']:x for x in state['events']}
    sources = {x['source_id']:x for x in state['sources']}
    missing=[]; mismatches=[]; original=[]
    for item in expected:
        source=item['source']; event=item['event']
        if source['source_id'] not in sources:
            missing.append(source['source_id'])
        elif sources[source['source_id']] != source:
            mismatches.append(source['source_id'])
        if event is None:
            continue
        original.append(event)
        saved=events.get(event['event_id'])
        if saved is None:
            missing.append(event['event_id'])
        elif any(saved.get(k)!=v for k,v in event.items()):
            mismatches.append(event['event_id'])
    # Numeric timestamps only: don't invent UTC for missing/naive text dates.
    numeric=[(i,e['occurred_at']) for i,e in enumerate(original)
             if type(e.get('occurred_at')) in (int,float)]
    reversals=[{'previous_message_id':original[a]['source_locator']['message_id'],
                'message_id':original[b]['source_locator']['message_id'],
                'previous_time':x,'time':y}
               for (a,x),(b,y) in zip(numeric,numeric[1:]) if y<x]
    return {'schema':'terminal-chat-check/v1','project_id':project_id,
            'session_id':session_id,'journal_tip':tip,
            'status':'PASS' if not missing and not mismatches else 'FAIL',
            'message_count':len(original),'text_characters':sum(len(e['text']) for e in original),
            'roles':dict(Counter(e['author'] for e in original)),
            'models':dict(Counter(str(e['model_id']) for e in original)),
            'repeated_text_message_count':len(original)-len({e['text'] for e in original}),
            'missing_ids':missing,'mismatched_ids':mismatches,
            'numeric_timestamp_reversals':reversals,
            'semantics':'Preservation after secret redaction only; messages remain reported. Reversed raw timestamps do not prove causal order.',
            'semantic_completion':'not_evaluated'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('root','project-id','input','session-id'):
        p.add_argument('--'+arg,required=True)
    args=p.parse_args()
    try:
        result=check_chat(args.root,args.project_id,json.loads(Path(args.input).read_text(encoding='utf-8')),args.session_id)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        p.exit(2,str(exc)+'\n')
    # ASCII-safe JSON on Windows stdout, Unicode values round-trip exactly.
    print(json.dumps(result,ensure_ascii=True,indent=2))
    raise SystemExit(0 if result['status']=='PASS' else 1)


if __name__=='__main__':
    main()
