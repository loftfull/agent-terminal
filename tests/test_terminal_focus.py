import unittest
from copy import deepcopy
from unittest.mock import patch
from terminal_focus import focus_summary
from terminal_brief import compile_brief


class FocusTests(unittest.TestCase):
    def test_small_index_keeps_all_blockers_and_unknown_eta(self):
        state = {'project':{'project_id':'p'},'handoff':{'next_step':'Check evidence'}}
        before = deepcopy(state)
        tasks = {str(i): {'task_id':str(i), 'status':'blocked', 'blockers':['block '+str(i)]} for i in range(8)}
        with patch('terminal_control.tasks_from_state', return_value=tasks):
            result = focus_summary(state)
        self.assertEqual(len(result['tasks']), 5)
        self.assertEqual(result['remaining_tasks'], 3)
        self.assertEqual(len(result['blockers']), 8)
        self.assertIsNone(result['eta'])
        self.assertIsNone(result['completion_percent'])
        self.assertEqual(state, before)

    def test_profile_is_optional_source_and_constraints_preserved(self):
        contract = {'task_id':'t','title':'Check','purpose':'Evidence','deliverables':['report'],
                    'acceptance':['18 messages'],'constraints':[{'rule':'No execution','reason':'archive'}],
                    'stop_conditions':['mismatch']}
        doc = {'contract':contract,'source_text':'Full source','output_profile':'focus'}
        result = compile_brief(doc)
        self.assertEqual(result['source_data'], doc)
        self.assertIn('Подача результата', result['markdown'])
        doc['output_profile'] = 'standard'
        self.assertNotIn('Подача результата', compile_brief(doc)['markdown'])
        self.assertEqual(compile_brief(doc)['contract']['constraints'], contract['constraints'])

    def test_invalid_profile_rejected(self):
        with self.assertRaises(ValueError):
            compile_brief({'contract':{},'output_profile':'execute everything'})
