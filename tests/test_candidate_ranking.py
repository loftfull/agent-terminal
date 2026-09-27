import unittest

from candidate_ranking import rank_history_candidates


class CandidateRankingTests(unittest.TestCase):
    def current(self):
        return {
            'chat_id': 'current',
            'title': 'Continue FIX Project History Agent',
            'text': 'continue project history agent durable memory',
            'continuation_refs': ['agent origin'],
            'project_id': 'project-history-agent',
            'repositories': ['https://github.com/loftfull/FIX'],
            'paths': ['C:/work/FIX'],
            'files': ['PROJECT_MEMORY.json'],
        }

    def test_explicit_chat_reference_outranks_repository_match(self):
        candidates = [
            {'session_id': 'repo', 'title': 'other', 'repositories': ['https://github.com/loftfull/FIX']},
            {'session_id': 'explicit', 'chat_id': 'old', 'title': 'Agent Origin', 'repositories': []},
        ]
        ranked = rank_history_candidates(self.current(), candidates)
        self.assertEqual('explicit', ranked[0]['session_id'])
        self.assertEqual('explicit_chat_reference', ranked[0]['rank_reason'])

    def test_exact_repository_outranks_project_plus_path(self):
        candidates = [
            {'session_id': 'combo', 'project_id': 'project-history-agent', 'paths': ['C:/work/FIX']},
            {'session_id': 'repo', 'repositories': ['HTTPS://GITHUB.COM/LOFTFULL/FIX.GIT/']},
        ]
        ranked = rank_history_candidates(self.current(), candidates)
        self.assertEqual(['repo', 'combo'], [x['session_id'] for x in ranked])
        self.assertEqual('exact_repository', ranked[0]['rank_reason'])
        self.assertEqual('project_plus_stable_identity', ranked[1]['rank_reason'])

    def test_exact_path_outranks_artifact_and_artifact_outranks_topic(self):
        candidates = [
            {'session_id': 'topic', 'title': 'Project History Agent durable memory'},
            {'session_id': 'artifact', 'files': ['PROJECT_MEMORY.json']},
            {'session_id': 'path', 'paths': ['c:/WORK/fix/']},
        ]
        ranked = rank_history_candidates(self.current(), candidates)
        self.assertEqual(['path', 'artifact', 'topic'], [x['session_id'] for x in ranked])
        self.assertEqual('exact_path', ranked[0]['rank_reason'])
        self.assertEqual('unique_artifact', ranked[1]['rank_reason'])
        self.assertEqual('topic_similarity', ranked[2]['rank_reason'])

    def test_project_id_without_stable_identity_is_below_exact_path(self):
        candidates = [
            {'session_id': 'project', 'project_id': 'project-history-agent'},
            {'session_id': 'path', 'paths': ['C:/work/FIX']},
        ]
        ranked = rank_history_candidates(self.current(), candidates)
        self.assertEqual(['path', 'project'], [x['session_id'] for x in ranked])
        self.assertEqual('project_id_only', ranked[1]['rank_reason'])

    def test_ranking_never_emits_lineage_decision(self):
        ranked = rank_history_candidates(self.current(), [
            {'session_id': 'repo', 'repositories': ['https://github.com/loftfull/FIX']},
        ])
        self.assertEqual('candidate-ranking-only', ranked[0]['authority'])
        self.assertNotIn('classification', ranked[0])
        self.assertNotIn('parent_chat_id', ranked[0])
        self.assertNotIn('continuation', ranked[0])

    def test_ranking_is_deterministic_for_equal_candidates(self):
        candidates = [
            {'session_id': 'b', 'title': 'unrelated'},
            {'session_id': 'a', 'title': 'unrelated'},
        ]
        first = rank_history_candidates(self.current(), candidates)
        second = rank_history_candidates(self.current(), list(reversed(candidates)))
        self.assertEqual(['a', 'b'], [x['session_id'] for x in first])
        self.assertEqual(['a', 'b'], [x['session_id'] for x in second])

    def test_no_signal_candidate_is_retained_but_ranked_last(self):
        ranked = rank_history_candidates(self.current(), [
            {'session_id': 'none', 'title': 'totally unrelated'},
            {'session_id': 'artifact', 'files': ['PROJECT_MEMORY.json']},
        ])
        self.assertEqual('artifact', ranked[0]['session_id'])
        self.assertEqual('no_stable_signal', ranked[-1]['rank_reason'])
        self.assertEqual(0, ranked[-1]['score'])


if __name__ == '__main__':
    unittest.main()
