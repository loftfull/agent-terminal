import json,tempfile,unittest
from pathlib import Path
from fix import attach
from terminal_context import read_layer

class ContextTests(unittest.TestCase):
    def test_progressive_read_preserves_sources_and_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);f=p/'input.json';m=p/'memory'
            f.write_text(json.dumps({'sessions':[{'session_id':'s','messages':[{'id':str(i),'role':'user','text':'Пример '+str(i)} for i in range(3)]}]}),encoding='utf-8')
            a=attach(m,'p',f,'s');b=attach(m,'p',f,'s')
            self.assertEqual(a['preservation']['message_count'],3);self.assertEqual(b['import']['messages_added'],0)
            self.assertFalse(a['continuous_ingestion'])
            l0=read_layer(m,'p');self.assertNotIn('items',l0)
            ids=[];offset=0
            while True:
                v=read_layer(m,'p','L2',offset,2);ids.extend(e['event_id'] for e in v['items'])
                for e in v['items']:
                    self.assertTrue(set(e['source_ids'])<={s['source_id'] for s in v['sources']})
                offset=v['next_offset']
                if offset is None:break
            self.assertEqual(len(ids),3);self.assertEqual(len(set(ids)),3)
            with self.assertRaises(ValueError):read_layer(m,'other')
            with self.assertRaises(ValueError):read_layer(m,'p','L2',-1)
            with self.assertRaises(ValueError):attach(m,'p',f,'missing')
    def test_original_export_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);f=p/'conversations.json'
            f.write_text(json.dumps([{'id':'s','title':'old','current_node':'n','mapping':{'n':{'id':'n','parent':None,'children':[],'message':{'id':'m','author':{'role':'user'},'content':{'content_type':'text','parts':['hello']}}}}}]))
            self.assertEqual(attach(p/'memory','p',f,'s')['preservation']['message_count'],1)
if __name__=='__main__':unittest.main()
