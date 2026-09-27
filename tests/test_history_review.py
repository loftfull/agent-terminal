import unittest
from history_review import review


class ReviewTests(unittest.TestCase):
    def fixture(self):
        return {'project_id':'p','sources':[{'source_id':'S'}],
                'work_items':[{'item_id':str(i),'project_id':'p','head_sha':str(i),
                               'base_sha':str(i-1),'category':'recovery',
                               'source_ids':['S'],'runtime_status':'not_run'} for i in range(4)],
                'decisions':[{'decision_id':'old','project_id':'p','source_ids':['S']},
                             {'decision_id':'new','project_id':'p','source_ids':['S'],'supersedes':'old'}]}

    def test_streak_is_not_completion_or_dead_end(self):
        result = review(self.fixture())
        self.assertEqual(4,result['longest_recovery_streak'])
        self.assertIsNone(result['completion_percentage'])
        self.assertEqual(0,result['reported_runtime_verified_count'])
        self.assertEqual('inferred',result['findings'][0]['status'])

    def test_explicit_supersession_preserves_old_decision(self):
        data=self.fixture(); result=review(data)
        self.assertEqual(['new'],[d['decision_id'] for d in result['active_decisions']])
        self.assertEqual(['old'],result['superseded_decision_ids'])
        self.assertEqual(2,len(data['decisions']))

    def test_serialized_review_retains_replaced_text_reason_and_source(self):
        import json
        data = self.fixture()
        data['decisions'][0].update(text='Удалять старую блокировку по возрасту',
                                   evidence_status='reported')
        data['decisions'][1].update(text='Использовать блокировку ОС',
                                   reason='Возраст не доказывает завершение владельца',
                                   evidence_status='reported')
        transferred = json.loads(json.dumps(review(data), ensure_ascii=False))
        self.assertEqual(transferred['decisions'], data['decisions'])
        self.assertEqual(transferred['superseded_decision_ids'], ['old'])
        self.assertEqual(transferred['active_decisions'][0]['decision_id'], 'new')

    def test_rejects_missing_evidence_and_other_project(self):
        for field,value in [('source_ids',['missing']),('project_id','other')]:
            data=self.fixture();data['work_items'][0][field]=value
            with self.assertRaises(ValueError):review(data)

    def test_cycle_rejected(self):
        data=self.fixture();data['decisions'][0]['supersedes']='new'
        with self.assertRaises(ValueError):review(data)

    def test_broken_chain_interrupts_streak(self):
        data=self.fixture();data['work_items'][2]['base_sha']='other'
        result=review(data)
        self.assertEqual(2,result['longest_recovery_streak'])
        self.assertEqual('CHAIN_GAP',result['findings'][0]['code'])

    def test_date_alone_does_not_supersede(self):
        data=self.fixture();data['decisions'][1].pop('supersedes')
        self.assertEqual(2,len(review(data)['active_decisions']))

    def test_json_handoff_preserves_all_sourced_constraints(self):
        data=self.fixture()
        data['critical_constraints']=[{'project_id':'p','source_ids':['S'],
                                     'text':'No fifth tab'},
                                     {'project_id':'p','source_ids':['S'],
                                      'text':'QA remains provenance-blocked'}]
        self.assertEqual(data['critical_constraints'],review(data)['critical_constraints'])
        data['critical_constraints'][0]['source_ids']=[]
        with self.assertRaises(ValueError):review(data)
