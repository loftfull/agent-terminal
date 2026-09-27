import copy
import tempfile
import unittest
from evidence_import import import_sessions
from terminal_chat_check import check_chat


class ChatCheckTests(unittest.TestCase):
    def test_repeated_prompts_and_dates_preserved(self):
        doc={'sessions':[{'session_id':'s','messages':[
            {'id':'1','role':'user','text':'Повтор','create_time':2},
            {'id':'2','role':'assistant','text':'Ответ','create_time':1,'metadata':{'model_slug':'explicit'}},
            {'id':'3','role':'user','text':'Повтор','create_time':None}]}]}
        with tempfile.TemporaryDirectory() as root:
            import_sessions(root,'p',doc,['s'])
            result=check_chat(root,'p',doc,'s')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['message_count'],3)
            self.assertEqual(result['repeated_text_message_count'],1)
            self.assertEqual(len(result['numeric_timestamp_reversals']),1)
            self.assertEqual(result['models'],{'unknown':2,'explicit':1})
            self.assertEqual(result['semantic_completion'],'not_evaluated')
            changed=copy.deepcopy(doc);changed['sessions'][0]['messages'][1]['text']='Different'
            self.assertEqual(check_chat(root,'p',changed,'s')['status'],'FAIL')
            with self.assertRaises(ValueError): check_chat(root,'wrong',doc,'s')

    def test_comparison_applies_same_secret_redaction(self):
        doc={'sessions':[{'session_id':'s','messages':[{'id':'1','role':'user','text':'https://u:password@example.com'}]}]}
        with tempfile.TemporaryDirectory() as root:
            import_sessions(root,'p',doc,['s'])
            self.assertEqual(check_chat(root,'p',doc,'s')['status'],'PASS')

if __name__=='__main__':unittest.main()
