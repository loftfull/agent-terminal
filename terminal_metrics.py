"""Evidence-derived counters, not a readiness estimator or live chat subscription."""
from collections import Counter
from terminal_control import tasks_from_state


def browser_observation(state):
    """Last journal observation, never a claim of current auth or subscription."""
    sources = {s.get('source_id') for s in state.get('sources', [])}
    last = None
    for event in state.get('events', []):
        if event.get('event_type') != 'chat_access_observation':
            continue
        refs = event.get('source_ids', [])
        valid = (isinstance(refs, list) and bool(refs)
                 and all(isinstance(s, str) and s in sources for s in refs))
        payload = event.get('browser_observation', {})
        if not isinstance(payload, dict):
            payload = {}
        last = {'event_id': event.get('event_id'),
                'evidence_status': event.get('evidence_status', 'unknown') if valid else 'unknown',
                'result': payload.get('result', 'unknown'),
                'observed_at': event.get('observed_at'),
                'source_ids': refs if valid else [],
                'current_chat_match': payload.get('current_chat_match', 'unknown'),
                'sample_messages': payload.get('sample_messages'),
                'coverage': 'partial; original completeness unknown'}
    return last


def metrics(state):
    tasks = list(tasks_from_state(state).values())
    total = sum(len(t['acceptance']) for t in tasks)
    results = Counter(r['result'] for t in tasks for r in t['acceptance_results'])
    imports = {e.get('session_id') for e in state.get('events', [])
               if e.get('event_type') == 'message_record' and e.get('session_id')}
    catalog = {}
    for e in state.get('events', []):
        if e.get('event_type') == 'integration_observation':
            p = e.get('integration', {})
            if p.get('id') and p.get('kind') in ('repository', 'dependency', 'plugin', 'skill'):
                catalog[p['id']] = dict(p, event_id=e['event_id'],
                    evidence_status=e.get('evidence_status','unknown'),
                    source_ids=e.get('source_ids',[]), observed_at=e.get('observed_at'))
    return {'project_percent': None,
        'criteria': {'total':total, 'reported_pass':results['pass'],
                     'reported_fail':results['fail'],
                     'not_run':total-results['pass']-results['fail'], 'accepted':0},
        'plans': dict(Counter(p.get('status','unknown') for p in state.get('plans',[]))),
        'integrations':list(catalog.values()),
        'chat': {'status':'not_connected', 'transport':'none',
                 'continuous_ingestion': False,
                 'last_browser_observation': browser_observation(state),
                 'imported_sessions':len(imports),
                 'message_observations':sum(e.get('event_type')=='message_record' for e in state.get('events',[])),
                 'detail':'Импорт и MCP не являются подпиской на текущий ChatGPT-чат. Полнота неизвестна.'}}
