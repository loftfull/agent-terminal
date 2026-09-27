"""Action-first presentation adapted from ayghri/i-have-adhd (MIT).

Presentation only: no diagnosis, invented ETA, task execution or lost evidence.
See third_party/i-have-adhd-LICENSE.txt and docs/GITHUB_SOLUTIONS.md.
"""
from project_history_journal import redact_secrets

FOCUS_RULES = [
    'Начинайте с результата или следующего разрешённого действия; выполняет его агент, если участие пользователя не требуется.',
    'Для нескольких действий используйте нумерованные шаги и показывайте текущий статус.',
    'Показывайте до пяти пунктов группы, оставляя остальные в доступной полной версии. Не скрывайте блокирующие условия.',
    'Сохраняйте источники, ограничения, неопределённость и классы доказательств. Не превращайте отчёт исполнителя в приёмку.',
    'Не выдумывайте время завершения. Убирайте отступления и пустые заверения; при доступных данных проверяйте причину ошибки самостоятельно.',
]


def focus_summary(state):
    """Derived concise index. Full tasks, evidence and blockers remain in state."""
    from terminal_control import tasks_from_state
    state = redact_secrets(state)
    tasks = list(tasks_from_state(state).values())
    priority = {'blocked': 0, 'needs_input': 0, 'review': 1, 'in_progress': 2, 'pending': 3}
    tasks.sort(key=lambda t: priority.get(t.get('status'), 4))
    active = tasks[0] if tasks else None
    next_step = state.get('handoff', {}).get('next_step') or 'Следующий шаг не зафиксирован.'
    items = [{'task_id': t['task_id'], 'title': t.get('contract', {}).get('title', t['task_id']),
              'status': t.get('status', 'unknown'), 'accepted': t.get('accepted', False)} for t in tasks]
    return {'schema': 'terminal-focus/v1', 'next_step': next_step,
            'next_step_authority': 'handoff text, not an executable command',
            'current_task_id': active['task_id'] if active else None,
            'tasks': items[:5], 'remaining_tasks': max(0, len(items)-5),
            'total_tasks': len(items), 'completion_percent': None,
            'blockers': [{'task_id': t['task_id'], 'items': t.get('blockers', [])}
                         for t in tasks if t.get('status') == 'blocked' or t.get('blockers')],
            'eta': None, 'rules': FOCUS_RULES.copy(),
            'authority': 'Presentation index only. Full evidence remains available.'}
