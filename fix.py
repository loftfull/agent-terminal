"""Quick local entry; never impersonates a live ChatGPT account connection."""
import argparse
import json
from pathlib import Path
from evidence_import import import_sessions
from history_adapters import ChatGPTExportHistoryAdapter
from terminal_chat_check import check_chat
from terminal_context import read_layer


def attach(root,project_id,path,session_id):
    document=json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(document,list):
        session=ChatGPTExportHistoryAdapter(path).inspect(session_id)
        if session is None:raise ValueError('Selected session absent')
        document={'sessions':[session]}
    result=import_sessions(root,project_id,document,[session_id])
    check=check_chat(root,project_id,document,session_id)
    if check['status']!='PASS':raise ValueError('Imported sample preservation failed')
    return {'status':'imported_and_checked','continuous_ingestion':False,
            'import':result,'preservation':check,'context':read_layer(root,project_id)}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('attach','context'):
        a=sub.add_parser(name);a.add_argument('--root',required=True);a.add_argument('--project-id',required=True)
        if name=='attach':
            a.add_argument('--input',required=True);a.add_argument('--session',required=True)
        else:
            a.add_argument('--level',choices=['L0','L1','L2'],default='L0');a.add_argument('--offset',type=int,default=0);a.add_argument('--limit',type=int,default=20)
    a=p.parse_args()
    try:
        result=attach(a.root,a.project_id,a.input,a.session) if a.command=='attach' else read_layer(a.root,a.project_id,a.level,a.offset,a.limit)
    except (ValueError,OSError,KeyError,TypeError):
        p.exit(2,'Source/project validation failed; check selected input and journal locally.\n')
    print(json.dumps(result,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
