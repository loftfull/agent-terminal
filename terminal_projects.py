"""Explicit local project registry and launch plans; never launches a process.

Example: python terminal_projects.py --registry projects.json list
PowerShell plans use the call operator and individually quoted arguments. Run
one selected plan in each terminal; the MCP plan belongs in an MCP host config.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from project_history_journal import ProjectLock, atomic_write_text, redact_secrets
from project_history_mcp import HistoryReader

SCHEMA = 'terminal-project-registry/v1'


def safe_text(value):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError('Nonempty text without control characters is required')
    if redact_secrets(value) != value:
        raise ValueError('Potential credential in registry value; provide a credential-free value')
    return value


def normalized_path(value):
    return safe_text(str(Path(safe_text(str(value))).expanduser().resolve()))


def normalize_entry(entry):
    if not isinstance(entry, dict) or set(entry) != {'project_id', 'memory_root', 'checkout_root', 'label'}:
        raise ValueError('Registry entry requires exactly project_id, memory_root, checkout_root, label')
    pid = safe_text(entry['project_id'])
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', pid):
        raise ValueError('Project ID must contain 1..128 ASCII letters, digits, dots, underscores or hyphens')
    return {'project_id': pid, 'memory_root': normalized_path(entry['memory_root']),
            'checkout_root': normalized_path(entry['checkout_root']), 'label': safe_text(entry['label'])}


def overlaps(a, b):
    a, b = Path(a), Path(b)
    return a == b or a in b.parents or b in a.parents


def validate_entries(entries):
    if not isinstance(entries, list):
        raise ValueError('Registry projects must be a list')
    result = [normalize_entry(e) for e in entries]
    ids, roots = set(), []
    for entry in result:
        if entry['project_id'] in ids:
            raise ValueError('Duplicate project ID')
        if any(overlaps(entry['memory_root'], old) for old in roots):
            raise ValueError('Conflicting memory roots')
        ids.add(entry['project_id']); roots.append(entry['memory_root'])
    return result


def read_registry(registry):
    path = Path(normalized_path(registry))
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or set(data) != {'schema', 'projects'} or data['schema'] != SCHEMA:
        raise ValueError('Unsupported registry schema')
    entries = validate_entries(data['projects'])
    if entries != data['projects']:
        raise ValueError('Stored registry paths must already be normalized absolute paths')
    return entries


def update_registry(registry, *, add=None, remove=None):
    if (add is None) == (remove is None):
        raise ValueError('Select exactly one registry mutation')
    path = Path(normalized_path(registry))
    with ProjectLock(path.with_name(path.name + '.lock')):
        entries = read_registry(path)
        if add is not None:
            entries = validate_entries(entries + [add])
        else:
            if not any(e['project_id'] == remove for e in entries):
                raise ValueError('Project ID is not registered')
            entries = [e for e in entries if e['project_id'] != remove]
        atomic_write_text(path, json.dumps({'schema': SCHEMA, 'projects': entries}, ensure_ascii=False, indent=2) + '\n')
    return entries


def probe_entry(entry):
    entry = normalize_entry(entry)
    result = {**entry, 'status': 'unverified', 'checkout_exists': Path(entry['checkout_root']).is_dir(), 'warnings': []}
    if overlaps(entry['memory_root'], entry['checkout_root']):
        result['warnings'].append('Memory and checkout overlap; watcher requires separate roots and is disabled in launch plan.')
    if not Path(entry['memory_root']).is_dir():
        result['status'] = 'missing-memory-root'
        return result
    try:
        _, tip = HistoryReader(entry['memory_root'], entry['project_id']).read()
        result.update(status='verified-memory' if result['checkout_exists'] else 'verified-memory-missing-checkout', journal_tip=tip)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
        # Avoid echoing arbitrary filesystem errors, credentials or stored content.
        result['status'] = 'invalid-memory-or-project-mismatch'
    return result


def powershell_command(argv):
    return '& ' + ' '.join("'" + safe_text(arg).replace("'", "''") + "'" for arg in argv)


def launch_plan(entry, python, code_root):
    entry = normalize_entry(entry)
    if not Path(python).is_absolute() or not Path(code_root).is_absolute():
        raise ValueError('Python executable and code root must be absolute paths')
    # Preserve a virtualenv interpreter symlink: resolving it can select the base
    # interpreter and silently lose the installed MCP dependencies.
    python = safe_text(str(Path(python).absolute()))
    code_root = Path(normalized_path(code_root))
    if not Path(python).is_file() or not code_root.is_dir():
        raise ValueError('Python executable or code directory is missing')
    for script in ('terminal_dashboard.py', 'history_watch.py', 'project_history_mcp.py'):
        if not (code_root / script).is_file():
            raise ValueError('Required agent script is missing')
    probe = probe_entry(entry)
    if probe['status'] not in {'verified-memory', 'verified-memory-missing-checkout'}:
        raise ValueError('Registered project memory must pass identity and integrity checks before planning launch')
    common = ['--root', entry['memory_root'], '--project-id', entry['project_id']]
    commands = {'dashboard': [python, str(code_root / 'terminal_dashboard.py'), *common],
                'mcp': [python, str(code_root / 'project_history_mcp.py'), *common]}
    if probe['checkout_exists'] and not overlaps(entry['memory_root'], entry['checkout_root']):
        commands['watch'] = [python, str(code_root / 'history_watch.py'), '--root', entry['checkout_root'],
                             '--memory-root', entry['memory_root'], '--project-id', entry['project_id'], '--watch', '--interval', '60']
    warnings = list(probe['warnings'])
    if not probe['checkout_exists']:
        warnings.append('Checkout is missing; watcher plan omitted.')
    return {'project_id': entry['project_id'], 'journal_tip': probe['journal_tip'], 'commands': commands,
            'powershell': {key: powershell_command(argv) for key, argv in commands.items()},
            'warnings': warnings, 'executed': False,
            'instructions': 'Run a selected PowerShell command in its own terminal. Configure MCP argv in your host. No scheduler or global hooks installed.'}


def main():
    # JSON is a UTF-8 interface, including redirected Windows console output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', required=True, type=Path)
    sub = parser.add_subparsers(dest='action', required=True)
    add = sub.add_parser('add')
    for field in ('project-id', 'memory-root', 'checkout-root', 'label'):
        add.add_argument('--' + field, required=True)
    remove = sub.add_parser('remove'); remove.add_argument('--project-id', required=True)
    sub.add_parser('list')
    launch = sub.add_parser('launch-plan')
    launch.add_argument('--project-id', required=True)
    launch.add_argument('--python', required=True)
    launch.add_argument('--code-root', required=True)
    args = parser.parse_args()
    try:
        if args.action == 'add':
            entries = update_registry(args.registry, add={key: getattr(args, key) for key in ('project_id', 'memory_root', 'checkout_root', 'label')})
            output = {'projects': [probe_entry(e) for e in entries]}
        elif args.action == 'remove':
            output = {'projects': update_registry(args.registry, remove=args.project_id)}
        elif args.action == 'list':
            output = {'projects': [probe_entry(e) for e in read_registry(args.registry)]}
        else:
            entry = next((e for e in read_registry(args.registry) if e['project_id'] == args.project_id), None)
            if entry is None:
                raise ValueError('Project ID is not registered')
            output = launch_plan(entry, args.python, args.code_root)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except (ValueError, OSError, TimeoutError):
        parser.exit(1, 'Registry operation failed; check schema, unique project identity, paths and journal integrity.\n')


if __name__ == '__main__':
    main()
