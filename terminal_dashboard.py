"""Read-only local control panel over a selected project's verified journal.

No model API, shell execution or arbitrary file-serving endpoint is exposed.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from project_history_journal import atomic_write_text, verify_journal_set
from project_history_mcp import HistoryReader

TEMPLATE = Path(__file__).resolve().parent / 'web' / 'terminal.html'


def build_view(root, project_id, *, mode='live', vault=None):
    from terminal_control import tasks_from_state
    reader = HistoryReader(root, project_id, vault=vault)
    state, tip = reader.read()
    verification = verify_journal_set(root)
    if not verification['ok'] or verification['last_hash'] != tip:
        raise ValueError('History changed during read; retry')
    tasks = tasks_from_state(state)
    if isinstance(tasks, dict):
        tasks = list(tasks.values())
    from terminal_runner import runs_from_state
    runs = runs_from_state(state)
    flattened = [{**task.get('contract', {}), **task} for task in tasks]
    from terminal_focus import focus_summary
    protection = {'status': 'not_configured', 'unprotected_records': verification['records']}
    if vault is not None:
        from terminal_vault import verify
        protection = verify(root, project_id, vault)
        if protection['journal_tip'] != tip:
            raise ValueError('History changed during vault check; retry')
    from terminal_metrics import metrics
    from terminal_versions import versions, screenshot_view
    releases = versions(state)
    version_cards = [dict(v, screenshot=screenshot_view(root, state, v) if i < 8 else {'status': 'NOT_LOADED'}) for i, v in enumerate(reversed(releases))]
    return {
        # Preserve every canonical field, including future additions. Derived UI
        # fields must not replace canonical data (except the envelope schema).
        **state,
        'canonical_schema': state['schema'],
        'schema': 'terminal-view/v1', 'mode': mode,
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'integrity': {'ok': True, 'records': verification['records'], 'journal_tip': tip},
        'project': state['project'], 'tasks': flattened, 'runs': runs,
        'metrics': metrics(state), 'plans': state.get('plans', []), 'versions': state.get('versions', []),
        'checkpoints': version_cards,
        'focus': focus_summary(state), 'protection': protection,
        'events': state.get('events', []), 'locations': state.get('locations', []),
        'lines': state.get('development_lines', []), 'visuals': state.get('visuals', []),
        'sources': state.get('sources', []), 'constraints': state['project'].get('constraints', []),
        'handoff': state.get('handoff', {}),
        'warnings': ['Статусы задач сообщены исполнителем и не подтверждают, что процесс сейчас работает.',
                     'Присутствие записи не подтверждает истинность её содержания.',
                     'Панель читает выбранный журнал. Недоступные чаты и компьютеры не подключены.']
    }


def render_page(view=None):
    template = TEMPLATE.read_text(encoding='utf-8')
    vendor = (TEMPLATE.parent / 'vendor' / 'nprogress.js').read_text(encoding='utf-8')
    template = template.replace('/* VENDORED_NPROGRESS */', vendor)
    template = template.replace('/* MESSAGE_LIBRARY */', (TEMPLATE.parent/'message_library.js').read_text(encoding='utf-8'))
    template = template.replace('/* PROGRESS_DASHBOARD */', (TEMPLATE.parent/'progress_dashboard.js').read_text(encoding='utf-8'))
    for marker_name, filename in [('VENDORED_LOADING_CSS', 'vendor/loading.css'), ('STUDIO_CSS', 'studio.css'), ('HUB_CSS', 'hub.css'), ('HUB_MODEL_JS', 'hub_model.js'), ('HUB_UI_JS', 'hub_ui.js'), ('STUDIO_JS', 'studio.js'), ('CONNECTIONS_JS', 'connections.js'), ('REPOSITORY_CACHE_JS', 'repository_cache.js'), ('CONNECT_UI_JS', 'connect_ui.js')]:
        template = template.replace('/* ' + marker_name + ' */', (TEMPLATE.parent / filename).read_text(encoding='utf-8'))
    icons = {p.stem: p.read_text(encoding='utf-8') for p in (TEMPLATE.parent/'vendor/hub-icons').glob('*.svg')}
    template = template.replace('/* HUB_ICONS */', 'const HUB_ICONS=' + json.dumps(icons).replace('<', '\\u003c') + ';')
    template = template.replace('/* HUB_FONT */', (TEMPLATE.parent/'vendor/hub-font/Manrope.base64').read_text().strip())
    marker = '<script id="initial-state" type="application/json">null</script>'
    if marker not in template:
        raise ValueError('Dashboard template state marker missing')
    if view is None:
        return template
    # JSON is inert, but HTML's parser still recognizes closing script tags.
    data = json.dumps(view, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    return template.replace(marker, "<script id='initial-state' type='application/json'>" + data + '</script>')


def make_server(root, project_id, *, port=8765, vault=None):
    if not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError('Invalid port')
    HistoryReader(root, project_id, vault=vault).read()  # Refuse a wrong project before opening a socket.

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log potentially sensitive request paths or query strings.

        def respond(self, code, payload, content_type):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self' https://api.github.com; font-src data:; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def trusted_request(self):
            expected = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            host = self.headers.get('Host', '')
            origin = self.headers.get('Origin')
            if host not in expected or (origin is not None and origin not in {'http://' + x for x in expected}):
                self.respond(403, b'Forbidden origin or host', 'text/plain; charset=utf-8')
                return False
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                self.respond(403, b'Cross-site request refused', 'text/plain; charset=utf-8')
                return False
            return True

        def do_GET(self):
            if not self.trusted_request():
                return
            route = urlsplit(self.path)
            if route.query or route.fragment:
                self.respond(404, b'Not found', 'text/plain; charset=utf-8')
                return
            try:
                if route.path == '/':
                    self.respond(200, render_page().encode('utf-8'), 'text/html; charset=utf-8')
                elif route.path == '/api/state':
                    self.respond(200, json.dumps(build_view(root, project_id, vault=vault), ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')
                else:
                    self.respond(404, b'Not found', 'text/plain; charset=utf-8')
            except (ValueError, OSError, KeyError, TypeError):
                self.respond(503, json.dumps({'error': 'Не удалось проверить журнал. Состояние не обновлено; запустите doctor.'}, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

        def do_POST(self):
            self.respond(405, b'Read-only dashboard', 'text/plain; charset=utf-8')

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--vault', help='External checkpoint DB for rollback protection')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--export', type=Path, help='Write a standalone static snapshot instead of starting server')
    args = parser.parse_args()
    if args.export:
        atomic_write_text(args.export, render_page(build_view(args.root, args.project_id, mode='snapshot', vault=args.vault)))
        print(str(args.export.resolve()))
    else:
        server = make_server(args.root, args.project_id, port=args.port, vault=args.vault)
        print(f'Локальная панель: http://127.0.0.1:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
