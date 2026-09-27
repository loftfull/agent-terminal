"""Deterministic review of explicitly curated evidence; never infer project identity.

Input classifications are reported assessments, not facts extracted by this module.
Commit counts are deliberately not converted into a completion percentage.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def review(data: dict) -> dict:
    project_id = data.get('project_id')
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError('Explicit project_id required')
    sources = data.get('sources', [])
    source_ids = {s['source_id'] for s in sources}
    if len(source_ids) != len(sources):
        raise ValueError('Duplicate source_id')
    items = data.get('work_items', [])
    decisions = data.get('decisions', [])
    constraints = data.get('critical_constraints', [])
    for record in items + decisions + constraints:
        if record.get('project_id') != project_id:
            raise ValueError('Cross-project record rejected')
        if not record.get('source_ids') or set(record['source_ids']) - source_ids:
            raise ValueError('Each assessment requires registered sources')
    by_id = {d['decision_id']: d for d in decisions}
    if len(by_id) != len(decisions):
        raise ValueError('Duplicate decision_id')
    superseded = set()
    for decision in decisions:
        seen = {decision['decision_id']}
        parent = decision.get('supersedes')
        while parent is not None:
            if parent not in by_id or parent in seen:
                raise ValueError('Missing or cyclic supersedes decision')
            seen.add(parent)
            superseded.add(parent)
            parent = by_id[parent].get('supersedes')
    # Independent decisions remain active together: recency alone is not authority.
    active = [d for d in decisions if d['decision_id'] not in superseded]
    seen_items = set()
    prior_head = None
    streak = longest = 0
    findings = []
    for item in items:
        identity = item['item_id']
        if identity in seen_items:
            raise ValueError('Duplicate work item')
        seen_items.add(identity)
        if prior_head is not None and item.get('base_sha') != prior_head:
            findings.append({'code':'CHAIN_GAP', 'item_id':identity,
                             'source_ids':item['source_ids']})
            streak = 0
        kind = item.get('category', 'unknown')
        if kind not in {'recovery', 'product', 'architecture', 'unknown'}:
            raise ValueError('Unknown work category')
        streak = streak + 1 if kind == 'recovery' else 0
        longest = max(longest, streak)
        prior_head = item.get('head_sha')
        if not prior_head:
            raise ValueError('Explicit head_sha required for lineage review')
    threshold = data.get('max_recovery_streak', 2)
    if type(threshold) is not int or threshold < 1:
        raise ValueError('Positive max_recovery_streak required')
    if longest > threshold:
        findings.append({'code':'RECOVERY_CONCENTRATION', 'status':'inferred',
                         'count':longest, 'threshold':threshold,
                         'meaning':'Review future work allocation; not proof that these fixes were unnecessary or violated a later policy.',
                         'source_ids':sorted({s for i in items if i.get('category') == 'recovery' for s in i['source_ids']})})
    return {'project_id':project_id, 'coverage':data.get('coverage', 'unknown'),
            'critical_constraints':constraints,
            'work_item_count':len(items), 'longest_recovery_streak':longest,
            'reported_runtime_verified_count':sum(i.get('runtime_status') == 'verified' for i in items),
            'completion_percentage':None,
            'completion_reason':'No complete acceptance denominator supplied; commits and PRs do not measure product completion.',
            # A standalone handoff must retain the replaced text and provenance,
            # not only IDs that require the unavailable original input to resolve.
            'decisions':decisions,
            'active_decisions':active, 'superseded_decision_ids':sorted(superseded),
            'findings':findings, 'sources':sources,
            'authority':'Analysis of explicitly supplied classifications and links only; no automatic dead-end declaration.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    print(json.dumps(review(json.loads(args.input.read_text(encoding='utf-8'))), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
