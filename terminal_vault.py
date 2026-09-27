"""Explicit external journal witness using eventsourcing's transactional SQLite recorder.

Does not replace the canonical journal or repair it in place. Capture only at
chosen boundaries; changes since the latest capture are not protected. A vault
on the same computer is not an off-device backup and can itself be rolled back.
"""
from __future__ import annotations
import argparse
from contextlib import closing, contextmanager, nullcontext
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
from uuid import NAMESPACE_URL, uuid5

from project_history_agent import render_markdown
from project_history_journal import (ProjectLock, atomic_save_state, atomic_write_text,
    journal_paths, redact_secrets, replay_journal_set, verify_journal_set)
from project_history_auditor import audit_state

SCHEMA = 'fix-journal-vault/v1'
MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 1024
MAX_ENVELOPE_BYTES = MAX_BYTES * 2


def _safe_name(name):
    return name == 'PROJECT_HISTORY.events.jsonl' or bool(re.fullmatch(
        r'PROJECT_HISTORY\.segments/[A-Za-z0-9_-][A-Za-z0-9_.-]*\.jsonl', name))


def _digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def _records(files):
    return [json.loads(line) for name in sorted(files) for line in files[name].splitlines() if line.strip()]


def _has_secret_key(value):
    # The canonical redactor masks dictionary values, but intentionally preserves
    # keys. A byte-exact archive must refuse credentials in keys, not rename them.
    if isinstance(value, dict):
        return any(redact_secrets(str(key)) != str(key) or _has_secret_key(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(_has_secret_key(item) for item in value)
    return False


def _validate(files, project_id):
    if (not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES or
            'PROJECT_HISTORY.events.jsonl' not in files or
            any(not isinstance(n, str) or not _safe_name(n) or redact_secrets(n) != n or not isinstance(v, str)
                for n, v in files.items())):
        raise ValueError('Invalid vault file manifest')
    if sum(len(v.encode('utf-8')) for v in files.values()) > MAX_BYTES:
        raise ValueError('Journal exceeds vault size limit')
    # Parse only inert JSON. Never deserialize Python event topics from a vault.
    for record in _records(files):
        if not isinstance(record, dict):
            raise ValueError('Archived journal records must be JSON objects')
        if redact_secrets(record) != record or _has_secret_key(record):
            raise ValueError('Journal contains unredacted secret patterns; capture refused')
    with tempfile.TemporaryDirectory(prefix='fix-vault-validate-') as temp:
        root = Path(temp)
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode('utf-8'))
        verification = verify_journal_set(root)
        if not verification['ok']:
            raise ValueError('Archived journal integrity failed')
        state = replay_journal_set(root)
        if state.get('project', {}).get('project_id') != project_id:
            raise ValueError('Vault project identity mismatch')
        if any(i.get('severity') == 'error' for i in audit_state(state)):
            raise ValueError('Archived state structural audit failed')
        return state, verification


def _capture_files(root, project_id, *, locked=True):
    root = Path(root).resolve(strict=True)
    # A read-only MCP/HTTP check must not create lock files in the project.
    # Before/copied/after tips below detect concurrent changes without a write.
    guard = ProjectLock(root / '.project-history.lock') if locked else nullcontext()
    with guard:
        paths = journal_paths(root)
        if any(p.is_symlink() or any(parent.is_symlink() for parent in p.parents
                                    if parent != root and root in parent.parents)
               for p in paths):
            raise ValueError('Journal files and segment directories must not be symlinks')
        if len(paths) > MAX_FILES or sum(p.stat().st_size for p in paths) > MAX_BYTES:
            raise ValueError('Journal exceeds vault size limit')
        before = verify_journal_set(root)
        files = {p.relative_to(root).as_posix(): p.read_bytes().decode('utf-8') for p in paths}
        _, copied = _validate(files, project_id)
        after = verify_journal_set(root)
        if (not before['ok'] or not after['ok'] or
                before['last_hash'] != copied['last_hash'] or
                after['last_hash'] != copied['last_hash'] or
                after['records'] != copied['records']):
            raise ValueError('Journal changed during vault capture')
        return files, copied


def _external(root, vault):
    root, vault = Path(root).resolve(), Path(vault).resolve()
    if vault == root or root in vault.parents:
        raise ValueError('Vault must be outside the project memory directory')
    return vault


def _datastore(database):
    from eventsourcing.sqlite import (SQLiteConnection, SQLiteConnectionPool,
        SQLiteDatastore, SQLITE3_DEFAULT_LOCK_TIMEOUT)
    from eventsourcing.persistence import InterfaceError

    class ClosingSQLiteConnectionPool(SQLiteConnectionPool):
        # Adapted from eventsourcing 9.5.5 SQLiteConnectionPool._create_connection.
        # Copyright (c) 2025 John Bywater, BSD-3-Clause.
        # Full notice: third_party/eventsourcing-LICENSE.txt.
        # Upstream does not close c if journal-mode setup fails before pool
        # registration. Windows then retains a lock on a corrupt database.
        def _create_connection(self):
            try:
                c = sqlite3.connect(database=self.db_name, uri=True,
                    check_same_thread=False, isolation_level=None,
                    cached_statements=True,
                    timeout=self.lock_timeout or SQLITE3_DEFAULT_LOCK_TIMEOUT)
            except (sqlite3.Error, TypeError) as exc:
                raise InterfaceError(exc) from exc
            try:
                if not self.is_sqlite_memory_mode and not self.is_journal_mode_wal:
                    with closing(c.cursor()) as cursor:
                        cursor.execute('PRAGMA journal_mode;')
                        mode = cursor.fetchone()[0]
                        if mode.lower() == 'wal':
                            self.is_journal_mode_wal = True
                        else:
                            cursor.execute('PRAGMA journal_mode=WAL;')
                            self.is_journal_mode_wal = True
                            self.journal_mode_was_changed_to_wal = True
                c.row_factory = sqlite3.Row
                return SQLiteConnection(sqlite_conn=c, max_age=self.max_age)
            except BaseException:
                c.close()
                raise

    datastore = SQLiteDatastore(database, lock_timeout=5, pool_size=1, max_overflow=0)
    # Datastore construction is lazy: replace only this instance's unused pool.
    # No SDK global, sqlite function, or other application's connection is changed.
    datastore.pool.close()
    datastore.pool = ClosingSQLiteConnectionPool(db_name=database, lock_timeout=5,
                                                 pool_size=1, max_overflow=0)
    return datastore


@contextmanager
def _recorder(vault, *, write=False):
    from eventsourcing.sqlite import SQLiteAggregateRecorder
    from eventsourcing.persistence import PersistenceError
    path = Path(vault).resolve()
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
    elif not path.is_file():
        raise FileNotFoundError('Vault is missing; refusing unprotected access')
    # URI escaping comes from pathlib, not from untrusted string concatenation.
    database = str(path) if write else path.as_uri() + '?mode=ro'
    datastore = None
    try:
        datastore = _datastore(database)
        recorder = SQLiteAggregateRecorder(datastore, events_table_name='fix_vault_events')
        if write:
            recorder.create_table()
        yield recorder
    except (sqlite3.Error, PersistenceError) as exc:
        # HTTP and MCP callers get a controlled failure without raw SQL, payloads
        # or parameters. Missing/corrupt witnesses never fall back to no witness.
        raise ValueError('Vault storage unavailable, corrupt, or changed concurrently') from exc
    finally:
        if datastore is not None:
            datastore.close()


def _latest(recorder, project_id):
    events = recorder.select_events(uuid5(NAMESPACE_URL, 'fix-vault:' + project_id), desc=True, limit=1)
    if not events:
        return None, None
    event = events[0]
    if event.topic != SCHEMA or len(event.state) > MAX_ENVELOPE_BYTES:
        raise ValueError('Invalid vault envelope')
    data = json.loads(event.state)
    if (not isinstance(data, dict) or data.get('schema') != SCHEMA or
            data.get('project_id') != project_id or not isinstance(data.get('files'), dict) or
            _digest(data['files']) != data.get('content_sha256')):
        raise ValueError('Vault content digest or identity mismatch')
    _, verification = _validate(data['files'], project_id)
    if data.get('records') != verification['records'] or data.get('journal_tip') != verification['last_hash']:
        raise ValueError('Vault checkpoint metadata mismatch')
    return event, data


def capture(root, project_id, vault):
    """Capture full exact UTF-8 journal files atomically; refuse any history rewind."""
    from eventsourcing.persistence import StoredEvent
    vault = _external(root, vault)
    files, verification = _capture_files(root, project_id)
    with _recorder(vault, write=True) as recorder:
        previous, old = _latest(recorder, project_id)
        if old:
            old_records, new_records = _records(old['files']), _records(files)
            if new_records[:len(old_records)] != old_records:
                raise ValueError('Journal rollback or divergence detected; vault not changed')
            if _digest(files) == old['content_sha256']:
                return {'status': 'unchanged', 'version': previous.originator_version,
                        'records': old['records'], 'journal_tip': old['journal_tip']}
        version = previous.originator_version + 1 if previous else 1
        data = {'schema': SCHEMA, 'project_id': project_id,
                'captured_at': datetime.now(timezone.utc).isoformat(),
                'files': files, 'content_sha256': _digest(files),
                'records': verification['records'], 'journal_tip': verification['last_hash']}
        encoded = json.dumps(data, ensure_ascii=False).encode('utf-8')
        if len(encoded) > MAX_ENVELOPE_BYTES:
            raise ValueError('Vault envelope exceeds size limit; checkpoint not written')
        recorder.insert_events([StoredEvent(uuid5(NAMESPACE_URL, 'fix-vault:' + project_id),
            version, SCHEMA, encoded)])
        # Read back the committed event. Conflicting writers fail via unique version.
        saved = recorder.select_events(uuid5(NAMESPACE_URL, 'fix-vault:' + project_id),
                                       gt=version-1, lte=version)
        if len(saved) != 1 or json.loads(saved[0].state) != data:
            raise ValueError('Vault persistence verification failed')
    return {'status': 'captured', 'version': version, 'records': data['records'],
            'journal_tip': data['journal_tip']}


def verify(root, project_id, vault):
    """Refuse missing witness, rollback, or divergence. Does not advance the witness."""
    vault = _external(root, vault)
    with _recorder(vault) as recorder:
        event, data = _latest(recorder, project_id)
        if event is None:
            raise ValueError('No vault checkpoint for this project')
    files, current = _capture_files(root, project_id, locked=False)
    archived = _records(data['files'])
    records = _records(files)
    if records[:len(archived)] != archived:
        raise ValueError('Journal rollback or divergence detected against external vault')
    return {'status': 'matched' if len(records) == len(archived) else 'ahead_of_vault',
            'version': event.originator_version, 'protected_records': len(archived),
            'current_records': len(records), 'unprotected_records': len(records)-len(archived),
            'journal_tip': current['last_hash'], 'vault_tip': data['journal_tip']}


def recover(project_id, vault, destination):
    """Export latest independently validated archive into a NEW directory only."""
    destination = Path(destination).resolve()
    _external(destination, vault)
    if destination.exists():
        raise FileExistsError('Recovery destination must not exist; original evidence is preserved')
    with _recorder(vault) as recorder:
        event, data = _latest(recorder, project_id)
        if event is None:
            raise ValueError('No vault checkpoint for this project')
    state, _ = _validate(data['files'], project_id)
    destination.mkdir(parents=True, exist_ok=False)
    for name, text in data['files'].items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle:
            handle.write(text.encode('utf-8'))
    atomic_save_state(destination / 'PROJECT_MEMORY.json', state)
    atomic_write_text(destination / 'PROJECT_MEMORY.md', render_markdown(state))
    result = verify(destination, project_id, vault)
    return dict(result, destination=str(destination), restored_from_version=event.originator_version)


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['capture', 'verify', 'recover'])
    parser.add_argument('--root')
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--destination')
    args = parser.parse_args()
    try:
        if args.command == 'recover':
            if not args.destination:
                parser.error('--destination is required for recover')
            result = recover(args.project_id, args.vault, args.destination)
        else:
            if not args.root:
                parser.error('--root is required')
            result = (capture if args.command == 'capture' else verify)(args.root, args.project_id, args.vault)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        # Diagnostics may contain paths, but never journal payload or SQL params.
        parser.exit(2, type(exc).__name__ + ': vault operation failed; check configuration and journal integrity\n')


if __name__ == '__main__':
    main()
