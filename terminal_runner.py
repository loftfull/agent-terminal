"""Explicit, bounded local command runner. No shell, model selection or retry loop.

Commands retain their normal host permissions: this is a supervisor, not a sandbox.
Only recognized secret patterns are redacted; arbitrary sensitive prose is not detected.
Journal output is bounded. A successful process never accepts a task automatically.
"""
from __future__ import annotations
import argparse
import contextlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone

from project_history_hooks import checkpoint
from project_history_journal import redact_secrets
from runtime_journal import append_mutation_set
from terminal_control import _load, tasks_from_state


def _now():
    return datetime.now(timezone.utc).isoformat()


@contextlib.contextmanager
def _runner_lock(root):
    """Kernel lock, released on crash. Never unlink a lock inode or steal by age."""
    path = Path(root) / '.terminal-runner.lock'
    with path.open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            raise TimeoutError('another command is running for this project') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def runs_from_state(state):
    runs = {}
    for event in state.get('events', []):
        if event.get('event_type') == 'terminal_run':
            item = event['runner_payload']
            runs[item['run_id']] = dict(item, event_id=event['event_id'])
    return list(runs.values())


def _record(root, payload):
    payload = redact_secrets(payload)
    eid = 'EV-RUN-' + payload['run_id'] + '-' + payload['status']
    sid = 'SRC-' + eid
    append_mutation_set(root, 'source.add', {'source_id': sid, 'kind': 'local_process',
        'locator': 'local-run:' + payload['run_id'], 'presence_status': 'observed',
        'content_status': 'observed', 'input': payload})
    append_mutation_set(root, 'event.add', {'event_id': eid, 'event_type': 'terminal_run',
        'evidence_status': 'observed', 'source_ids': [sid], 'author': 'local command supervisor',
        'summary': 'Local run ' + payload['status'], 'occurred_at': _now(),
        'model_id': payload['model_id'], 'session_id': payload['session_id'], 'runner_payload': payload})
    state = checkpoint(root)
    # A receipt may be used immediately as task evidence. Never return an ID
    # unless the journal replay actually contains its event and source.
    saved_event = next((e for e in state['events'] if e.get('event_id') == eid), None)
    saved_source = next((s for s in state['sources'] if s.get('source_id') == sid), None)
    if (saved_event is None or saved_source is None or
            saved_event.get('runner_payload') != payload or saved_source.get('input') != payload):
        raise RuntimeError('runner receipt persistence verification failed')
    return dict(payload, event_id=eid)


def _restore_unlocked(root, project_id):
    recovered = []
    for run in runs_from_state(_load(root, project_id)):
        if run['status'] in {'starting', 'running'}:
            run.pop('event_id', None)
            run.update(status='interrupted', ended_at=_now(), exit_code=None,
                       interruption_reason='previous supervisor ended without a completion record',
                       child_process_state='unknown', accepted=False)
            recovered.append(_record(root, run))
    return recovered


def restore_runs(root, project_id):
    """Recover orphaned journal statuses; never kill a possibly reused stored PID."""
    root = Path(root).resolve()
    _load(root, project_id)
    with _runner_lock(root):
        return _restore_unlocked(root, project_id)


def _safe_argv(argv):
    out = []
    hide_next = False
    for arg in argv:
        if hide_next:
            out.append('[REDACTED]')
            hide_next = False
            continue
        out.append(redact_secrets(arg))
        if re.search(r'^--?(?:.*[-_])?(?:token|password|passwd|secret|api[-_]?key|authorization|cookie|credential)$', arg, re.I):
            hide_next = True
    return out


class _Capture:
    def __init__(self, pipe, limit):
        self.pipe, self.limit = pipe, limit
        self.data = bytearray()
        self.total = 0
        self.error = None
        self.thread = threading.Thread(target=self.read, daemon=True)

    def read(self):
        try:
            while True:
                chunk = os.read(self.pipe.fileno(), 8192)
                if not chunk:
                    break
                self.total += len(chunk)
                available = self.limit - len(self.data)
                if available > 0:
                    self.data.extend(chunk[:available])
        except (OSError, ValueError):
            self.error = 'output read interrupted'
        finally:
            self.pipe.close()

    def result(self):
        truncated = self.total > self.limit
        data = bytes(self.data)
        if truncated:
            # Never persist a credential fragment cut in the middle of a line.
            last_line = data.rfind(b'\n')
            data = data[:last_line + 1] if last_line >= 0 else b''
        text = redact_secrets(data.decode('utf-8', errors='replace'))
        encoded = text.encode('utf-8')
        if len(encoded) > self.limit:
            text = encoded[:self.limit].decode('utf-8', errors='ignore')
            truncated = True
        return {'text': text, 'bytes_seen': self.total, 'truncated': truncated,
                'capture_error': self.error}


class _WindowsJob:
    """Assign a suspended process to a kill-on-close job before executing code."""
    def __init__(self, process):
        import ctypes
        from ctypes import wintypes as w
        self.c = ctypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.k = k
        class BASIC(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                        ('LimitFlags', w.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                        ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', w.DWORD),
                        ('Affinity', ctypes.c_size_t), ('PriorityClass', w.DWORD), ('SchedulingClass', w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ('ReadOperationCount', 'WriteOperationCount',
                'OtherOperationCount', 'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]
        class EXT(ctypes.Structure):
            _fields_ = [('BasicLimitInformation', BASIC), ('IoInfo', IO), ('ProcessMemoryLimit', ctypes.c_size_t),
                ('JobMemoryLimit', ctypes.c_size_t), ('PeakProcessMemoryUsed', ctypes.c_size_t),
                ('PeakJobMemoryUsed', ctypes.c_size_t)]
        class THREAD(ctypes.Structure):
            _fields_ = [('dwSize', w.DWORD), ('cntUsage', w.DWORD), ('th32ThreadID', w.DWORD),
                ('th32OwnerProcessID', w.DWORD), ('tpBasePri', w.LONG), ('tpDeltaPri', w.LONG), ('dwFlags', w.DWORD)]
        for name, restype, args in (
            ('CreateJobObjectW', w.HANDLE, [ctypes.c_void_p, w.LPCWSTR]),
            ('SetInformationJobObject', w.BOOL, [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]),
            ('AssignProcessToJobObject', w.BOOL, [w.HANDLE, w.HANDLE]),
            ('CloseHandle', w.BOOL, [w.HANDLE]),
            ('CreateToolhelp32Snapshot', w.HANDLE, [w.DWORD, w.DWORD]),
            ('Thread32First', w.BOOL, [w.HANDLE, ctypes.POINTER(THREAD)]),
            ('Thread32Next', w.BOOL, [w.HANDLE, ctypes.POINTER(THREAD)]),
            ('OpenThread', w.HANDLE, [w.DWORD, w.BOOL, w.DWORD]),
            ('ResumeThread', w.DWORD, [w.HANDLE])):
            fn = getattr(k, name)
            fn.restype, fn.argtypes = restype, args
        self.handle = k.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            limits = EXT()
            limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not k.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                raise ctypes.WinError(ctypes.get_last_error())
            if not k.AssignProcessToJobObject(self.handle, w.HANDLE(int(process._handle))):
                raise ctypes.WinError(ctypes.get_last_error())
            snapshot = k.CreateToolhelp32Snapshot(4, 0)  # TH32CS_SNAPTHREAD
            if snapshot == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            resumed = False
            try:
                entry = THREAD()
                entry.dwSize = ctypes.sizeof(entry)
                found = k.Thread32First(snapshot, ctypes.byref(entry))
                while found:
                    if entry.th32OwnerProcessID == process.pid:
                        thread = k.OpenThread(2, False, entry.th32ThreadID)
                        if not thread:
                            raise ctypes.WinError(ctypes.get_last_error())
                        try:
                            if k.ResumeThread(thread) == 0xFFFFFFFF:
                                raise ctypes.WinError(ctypes.get_last_error())
                            resumed = True
                        finally:
                            k.CloseHandle(thread)
                    found = k.Thread32Next(snapshot, ctypes.byref(entry))
            finally:
                k.CloseHandle(snapshot)
            if not resumed:
                raise OSError('cannot resume supervised process thread')
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None


def _terminate(process, job):
    if os.name == 'nt':
        if job is not None:
            job.close()  # includes children even after the process-group leader exits
        else:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def run_command(root, project_id, task_id, argv, cwd, timeout=60, model_id='unknown',
                session_id='unknown', continuation_count=0, max_output_bytes=65536, vault=None):
    """Execute one explicitly selected argv, exactly once; no shell or silent retries."""
    root = Path(root).resolve()
    state = _load(root, project_id)
    if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or not a or '\x00' in a for a in argv):
        raise ValueError('argv must be nonempty list of nonempty strings without NUL')
    if not isinstance(cwd, (str, Path)) or not str(cwd) or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
        raise ValueError('cwd must name an explicit existing absolute directory')
    if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise ValueError('timeout must be finite seconds > 0 and <= 86400')
    if type(max_output_bytes) is not int or not 256 <= max_output_bytes <= 1048576:
        raise ValueError('max_output_bytes must be an integer from 256 to 1048576 per stream')
    if any(not isinstance(v, str) or not v.strip() for v in (model_id, session_id)):
        raise ValueError('model_id and session_id must be explicit strings or unknown')
    # Windows may implicitly execute batch files using cmd.exe even with shell=False.
    if os.name == 'nt' and Path(argv[0]).suffix.lower() in {'.bat', '.cmd'}:
        raise ValueError('batch commands are not supported; select an executable explicitly')
    with _runner_lock(root):
        if vault is not None:
            from terminal_vault import capture as capture_vault, verify as verify_vault
            verify_vault(root, project_id, vault)  # Missing witness must not be silently recreated.
            capture_vault(root, project_id, vault)  # Abort a rewind before launching anything.
        _restore_unlocked(root, project_id)
        state = _load(root, project_id)
        task = tasks_from_state(state).get(task_id)
        if task is None:
            raise ValueError('existing task contract required')
        previous = [r for r in runs_from_state(state) if r['task_id'] == task_id]
        minimum = max([task['continuation_count']] + [r['continuation_count'] + 1 for r in previous])
        if type(continuation_count) is not int or not minimum <= continuation_count <= task['max_continuations']:
            raise ValueError('continuation_count must advance for retries and stay within contract limit')
        payload = {'run_id': uuid.uuid4().hex, 'project_id': project_id, 'task_id': task_id,
            'argv': _safe_argv(argv), 'cwd': str(Path(cwd).resolve()), 'timeout_seconds': timeout,
            'model_id': model_id, 'session_id': session_id, 'attribution_status': 'reported',
            'continuation_count': continuation_count,
            'started_at': _now(), 'ended_at': None, 'exit_code': None, 'status': 'starting',
            'accepted': False, 'runner_pid': os.getpid(), 'process_id': None,
            'output_limit_per_stream_bytes': max_output_bytes}
        start = _record(root, payload)
        payload['start_event_id'] = start['event_id']
        process = job = None
        terminated = False
        captures = []
        deadline = time.monotonic() + timeout
        try:
            kwargs = {'cwd': str(cwd), 'stdin': subprocess.DEVNULL, 'stdout': subprocess.PIPE,
                      'stderr': subprocess.PIPE, 'shell': False, 'close_fds': True}
            if os.name == 'nt':
                kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | 4  # CREATE_SUSPENDED
            else:
                kwargs['start_new_session'] = True
            process = subprocess.Popen(argv, **kwargs)
            if os.name == 'nt':
                job = _WindowsJob(process)
            payload.update(process_id=process.pid, status='running')
            _record(root, payload)
            captures = [_Capture(process.stdout, max_output_bytes), _Capture(process.stderr, max_output_bytes)]
            for capture in captures:
                capture.thread.start()
            while process.poll() is None or any(c.thread.is_alive() for c in captures):
                if time.monotonic() >= deadline:
                    payload['status'] = 'timed_out'
                    break
                time.sleep(min(0.02, max(0, deadline - time.monotonic())))
            else:
                payload['status'] = 'succeeded' if process.returncode == 0 else 'failed'
            _terminate(process, job)  # clear descendants on normal exit too
            job = None
            terminated = True
            for capture in captures:
                capture.thread.join(timeout=2)
            payload.update(exit_code=process.returncode, stdout=captures[0].result(), stderr=captures[1].result())
        except (KeyboardInterrupt, SystemExit):
            payload.update(status='interrupted', interruption_reason='supervisor interrupted')
            raise
        except Exception as exc:
            payload.update(status='launch_error' if process is None else 'supervisor_error',
                           error=redact_secrets(str(exc)))
        finally:
            if process is not None:
                if not terminated:
                    _terminate(process, job)
                for capture in captures:
                    capture.thread.join(timeout=2)
                if captures:
                    payload.update(stdout=captures[0].result(), stderr=captures[1].result())
                payload['exit_code'] = process.returncode
                if not captures:
                    for pipe in (process.stdout, process.stderr):
                        if pipe is not None:
                            pipe.close()
            payload['ended_at'] = _now()
            result = _record(root, payload)
            if vault is not None:
                result['vault_checkpoint'] = capture_vault(root, project_id, vault)
        return result


def main():
    # Machine-readable receipts are UTF-8 regardless of Windows console/codepage.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, help='UTF-8 JSON with explicit run_command arguments')
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text(encoding='utf-8'))
    if not isinstance(request, dict):
        parser.error('request must be a JSON object')
    result = run_command(**request)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'succeeded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
