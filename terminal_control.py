"""Append-only task contracts and reported execution state. Never executes commands.

A done report is displayed as review, never accepted. Evidence references establish
traceability only: even an observed message does not establish executed acceptance.
Contracts are immutable; revisions require a new task_id. State is journal-derived.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from project_history_hooks import checkpoint
from project_history_agent import render_markdown
from project_history_journal import atomic_save_state, atomic_write_text
from project_history_journal import ProjectLock, redact_secrets, replay_journal_set, verify_journal_set, journal_paths
from runtime_journal import append_mutation_set


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be nonempty string')
    return value


def _strings(value, name, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f'{name} must be list' + (' with entries' if nonempty else ''))
    for item in value:
        _text(item, name)
    if len(set(value)) != len(value):
        raise ValueError(f'{name} contains duplicates')
    return value


def _integer(value, name, maximum):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f'{name} must be integer from 0 to {maximum}')
    return value


def _contract(document):
    if not isinstance(document, dict):
        raise ValueError('contract must be object')
    allowed = {'task_id','title','purpose','deliverables','acceptance','constraints','stop_conditions','max_continuations'}
    if set(document) - allowed:
        raise ValueError('unknown contract fields')
    out = {key: _text(document.get(key), key) for key in ('task_id','title','purpose')}
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', out['task_id']):
        raise ValueError('task_id must be stable ASCII identifier')
    for key in ('deliverables','acceptance','stop_conditions'):
        out[key] = _strings(document.get(key), key, nonempty=True)
    constraints = document.get('constraints')
    if not isinstance(constraints, list):
        raise ValueError('constraints must be list')
    out['constraints'] = []
    for c in constraints:
        if not isinstance(c, dict) or set(c) != {'rule','reason'}:
            raise ValueError('constraint requires rule and reason')
        out['constraints'].append({k: _text(c[k], k) for k in ('rule','reason')})
    out['max_continuations'] = _integer(document.get('max_continuations',2),'max_continuations',3)
    clean = redact_secrets(out)
    if clean['task_id'] != out['task_id']:
        raise ValueError('task_id cannot contain credentials')
    for key in ('deliverables','acceptance','stop_conditions'):
        _strings(clean[key],key,nonempty=True)
    return clean


def _load(root, project_id):
    _text(project_id, 'project_id')
    if not journal_paths(root):
        raise ValueError('existing project journal required')
    if not verify_journal_set(root)['ok']:
        raise ValueError('journal integrity failure')
    state = replay_journal_set(root)
    if state['project']['project_id'] != project_id:
        raise ValueError('project_id mismatch')
    return state


def tasks_from_state(state):
    tasks = {}
    preceding = []
    for event in state['events']:
        kind = event.get('event_type')
        if kind == 'terminal_contract':
            contract = _contract(event['terminal_payload'])
            if contract != event['terminal_payload']:
                raise ValueError('noncanonical terminal contract in journal')
            tid = contract['task_id']
            if tid in tasks:
                raise ValueError('duplicate terminal contract in journal')
            tasks[tid] = {**contract, 'contract':contract, 'status':'queued',
                'reported_status':'queued', 'summary':'', 'model_id':'unknown', 'session_id':'unknown',
                'continuation_count':0, 'blockers':[], 'acceptance_results':[],
                'evidence_event_ids':[], 'accepted':False, 'observed_at':event.get('occurred_at'),
                'contract_event_id':event['event_id'], 'report_event_id':None}
        elif kind == 'terminal_report':
            report = event['terminal_payload']
            if report['task_id'] not in tasks:
                raise ValueError('terminal report without contract')
            task = tasks[report['task_id']]
            validated = _report(report, task, {'events':preceding})
            if validated != report:
                raise ValueError('noncanonical terminal report in journal')
            task.update(report)
            task.update(reported_status=report['status'], status='review' if report['status']=='done' else report['status'],
                        accepted=False, observed_at=event.get('occurred_at'), report_event_id=event['event_id'])
        preceding.append(event)
    return tasks


def terminal_status(root, project_id):
    state = _load(Path(root), project_id)
    tasks = list(tasks_from_state(state).values())
    counts = {key:sum(t['status']==key for t in tasks) for key in ('queued','running','blocked','review','done')}
    return {'project_id':project_id,'tasks':tasks,'counts':counts,'accepted_count':0,
            'status_semantics':'reported; not process heartbeat', 'acceptance_gate':'not_implemented'}


def _report(document, task, state):
    if not isinstance(document, dict):
        raise ValueError('report must be object')
    allowed = {'task_id','status','summary','model_id','session_id','evidence_event_ids','blockers','acceptance_results','continuation_count'}
    if set(document) - allowed:
        raise ValueError('unknown report fields')
    out = {k:_text(document.get(k),k) for k in ('task_id','status','summary')}
    if out['status'] not in {'queued','running','blocked','review','done'}:
        raise ValueError('invalid report status')
    for key in ('model_id','session_id'):
        out[key] = _text(document.get(key,'unknown'),key)
    out['continuation_count'] = _integer(document.get('continuation_count',0),'continuation_count',task['max_continuations'])
    if out['continuation_count'] < task['continuation_count']:
        raise ValueError('continuation_count cannot decrease')
    known = {e['event_id'] for e in state['events']}
    def refs(value):
        values = _strings(value,'evidence_event_ids')
        if set(values) - known:
            raise ValueError('unknown evidence event reference')
        return values
    out['evidence_event_ids'] = refs(document.get('evidence_event_ids',[]))
    out['blockers'] = _strings(document.get('blockers',[]),'blockers')
    if out['status']=='blocked' and not out['blockers']:
        raise ValueError('blocked report requires blockers')
    results = document.get('acceptance_results',[])
    if not isinstance(results,list):
        raise ValueError('acceptance_results must be list')
    out['acceptance_results'] = []
    seen=set()
    for result in results:
        if not isinstance(result,dict) or set(result)!={'criterion','result','evidence_event_ids'}:
            raise ValueError('acceptance result requires criterion, result, evidence_event_ids')
        criterion = _text(result['criterion'],'criterion')
        if criterion not in task['acceptance'] or criterion in seen:
            raise ValueError('unknown or duplicate acceptance criterion')
        seen.add(criterion)
        if result['result'] not in {'pass','fail','not_run'}:
            raise ValueError('invalid acceptance result')
        evidence = refs(result['evidence_event_ids'])
        if result['result']=='pass' and not evidence:
            raise ValueError('reported pass requires evidence reference')
        out['acceptance_results'].append(dict(result, evidence_event_ids=evidence))
    return redact_secrets(out)


def _write(root, project_id, document, kind):
    root=Path(root).resolve()
    if not root.is_dir():
        raise ValueError('existing project root required')
    with ProjectLock(root/'.terminal-control.lock',timeout=30):
        state=_load(root,project_id)
        tasks=tasks_from_state(state)
        if kind=='terminal_contract':
            payload=_contract(document)
            old=tasks.get(payload['task_id'])
            if old and old['contract'] != payload:
                raise ValueError('immutable task contract; use new task_id')
        else:
            if not isinstance(document,dict) or not isinstance(document.get('task_id'),str) or document['task_id'] not in tasks:
                raise ValueError('unknown task_id')
            # Normalize against zero first so exact retries remain idempotent after later reports.
            old=tasks[document['task_id']]
            payload=_report(document,dict(old,continuation_count=0),state)
        digest=hashlib.sha256(json.dumps([project_id,kind,payload],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        eid='EV-TERMINAL-'+digest
        known={e['event_id'] for e in state['events']}
        added=eid not in known
        if added:
            if kind=='terminal_report':
                _report(document,old,state)
            sid='SRC-TERMINAL-'+digest
            if sid not in {s['source_id'] for s in state['sources']}:
                append_mutation_set(root,'source.add',{'source_id':sid,'kind':'terminal_cli',
                    'locator':'terminal-cli:'+payload['task_id']+'/'+digest,'content_status':'reported',
                    'presence_status':'observed','input':payload})
            append_mutation_set(root,'event.add',{'event_id':eid,'event_type':kind,'evidence_status':'reported',
                'summary':payload.get('summary',payload.get('title')),'source_ids':[sid],
                'model_id':payload.get('model_id','unknown'),
                'session_id':payload.get('session_id','unknown'),
                'author':'reported executor' if kind=='terminal_report' else 'contract submitter',
                'occurred_at':datetime.now(timezone.utc).isoformat(),'terminal_payload':payload})
        if added:
            checkpoint(root)
        else:
            # Repair projections without appending handoff timestamps on retries.
            with ProjectLock(root/'.project-history.snapshot.lock',timeout=5):
                current = _load(root,project_id)
                snapshot=root/'PROJECT_MEMORY.json'
                try:
                    matches=json.loads(snapshot.read_text(encoding='utf-8'))==current
                except (OSError,ValueError):
                    matches=False
                if not matches:
                    atomic_save_state(snapshot,current)
                report=root/'PROJECT_MEMORY.md'
                markdown=render_markdown(current)
                if not report.exists() or report.read_text(encoding='utf-8')!=markdown:
                    atomic_write_text(report,markdown)
        task=tasks_from_state(_load(root,project_id))[payload['task_id']]
        return {'event_id':eid,'added':added,'task':task}


def submit_contract(root, project_id, document):
    return _write(root,project_id,document,'terminal_contract')


def record_report(root, project_id, document):
    return _write(root,project_id,document,'terminal_report')


def render_tasks(state):
    """Read-only TASKS projection; journal remains authoritative.

    Escape Markdown control characters so reported text stays text, not images,
    links, headings or executable HTML in a preview.
    """
    def text(value):
        value=str(value).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        for char in ('\\','`','*','_','{','}','[',']','(',')','#','+','-','.','!','|'):
            value=value.replace(char,'\\'+char)
        return value.replace('\r','').replace('\n',' / ')
    lines=['# TASKS', '', 'Source: project journal. Status is reported, not a process heartbeat.',
           'Acceptance gate is not implemented; done reports require review.', '',
           'Project: '+text(state['project']['project_id']), '']
    tasks=tasks_from_state(state)
    if not tasks:
        lines += ['No task contracts recorded.', '']
    for task in tasks.values():
        lines += ['## '+text(task['task_id'])+' — '+text(task['title']), '',
                  '- Status: '+text(task['status'])+'; reported status: '+text(task['reported_status']),
                  '- Accepted: false', '- Purpose: '+text(task['purpose']),
                  '- Model: '+text(task['model_id'])+'; session: '+text(task['session_id']),
                  '- Observed at: '+text(task['observed_at'] or 'unknown'),
                  '- Continuations: '+str(task['continuation_count'])+' / '+str(task['max_continuations']),
                  '- Summary: '+text(task['summary'] or 'No report'), '', '### Deliverables', '']
        lines += ['- '+text(item) for item in task['deliverables']]
        lines += ['', '### Acceptance criteria', '']
        results={item['criterion']:item for item in task['acceptance_results']}
        for criterion in task['acceptance']:
            result=results.get(criterion)
            lines += ['- '+text(criterion)+' — reported result: '+(result['result'] if result else 'not_run')]
            if result and result['evidence_event_ids']:
                lines += ['  Evidence: '+', '.join(text(ref) for ref in result['evidence_event_ids'])]
        lines += ['', '### Constraints and reasons', '']
        lines += ['- '+text(item['rule'])+' — '+text(item['reason']) for item in task['constraints']] or ['- None specified']
        lines += ['', '### Stop conditions', '']
        lines += ['- '+text(item) for item in task['stop_conditions']]
        lines += ['', '### Reported blockers', '']
        lines += ['- '+text(item) for item in task['blockers']] or ['- None reported']
        lines += ['', '### Evidence events', '']
        lines += ['- '+text(item) for item in task['evidence_event_ids']] or ['- None referenced']
        lines += ['', 'Contract event: '+text(task['contract_event_id']),
                  'Report event: '+text(task['report_event_id'] or 'none'), '']
    return '\n'.join(lines)+'\n'


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True)
    parser.add_argument('--project-id',required=True)
    subs=parser.add_subparsers(dest='command',required=True)
    for name in ('submit','report'):
        subs.add_parser(name).add_argument('--input',required=True)
    subs.add_parser('status').add_argument('--markdown',action='store_true')
    args=parser.parse_args()
    try:
        if args.command=='status':
            if args.markdown:
                print(render_tasks(_load(Path(args.root),args.project_id)),end='')
                return
            result=terminal_status(args.root,args.project_id)
        else:
            document=json.loads(Path(args.input).read_text(encoding='utf-8'))
            result=(submit_contract if args.command=='submit' else record_report)(args.root,args.project_id,document)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as exc:
        parser.exit(2, str(exc)+'\n')


if __name__=='__main__':
    main()
