"""Named code checkpoints and non-destructive restore using installed Git.

Journal remains at explicit memory root. Application refuses replacing a checkpoint;
Git administrators can still modify refs. No reset/stash or automatic execution.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import stat
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from project_history_journal import ProjectLock, atomic_write_text
from project_history_hooks import checkpoint
from project_history_mcp import HistoryReader
from runtime_journal import append_mutation_set


def local_git_env():
    # These operations are local. Do not inherit global/system filter executables.
    return dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')


def git(repo, *args):
    r = subprocess.run(['git','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false',
                        '-c','submodule.recurse=false','-C',str(repo),*args],
                       capture_output=True, text=True, encoding='utf-8', timeout=90, env=local_git_env())
    if r.returncode: raise ValueError('Git operation failed: '+r.stderr.strip())
    return r.stdout.strip()


def refuse_filters(repo):
    # Configured filters can execute arbitrary commands even with Git hooks off.
    r=subprocess.run(['git','-C',str(repo),'config','--name-only','--get-regexp',
                      r'^filter\..*\.(clean|smudge|process)$'],capture_output=True,
                     text=True,encoding='utf-8',timeout=15,env=local_git_env())
    if r.returncode not in (0,1):raise ValueError('Cannot inspect Git filters')
    if r.stdout.strip():raise ValueError('Configured Git filters: checkpoint/restore refused; no filter executed')


def bounded_image_bytes(path):
    path=Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Image must be a regular non-symlink file')
    flags=os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_NOFOLLOW',0)
    fd=os.open(path,flags)
    with os.fdopen(fd,'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):raise ValueError('Image must be regular')
        data=handle.read(5*1024*1024+1)
    if len(data)>5*1024*1024:raise ValueError('Image exceeds5MiB')
    return data


def versions(state):
    return [v for v in state.get('versions',[]) if v.get('checkpoint_schema')=='fix-code-checkpoint/v1']


def _read(root,pid):
    return HistoryReader(root,pid).read()[0]


def create(root,pid,repo,label,summary,evidence_event_ids):
    root=Path(root).resolve();repo=Path(repo).resolve()
    if not re.fullmatch(r'v\d+\.\d+\.\d+-candidate\.\d+',label):
        raise ValueError('Expected vMAJOR.MINOR.PATCH-candidate.N')
    if not isinstance(summary,str) or not summary.strip(): raise ValueError('Summary required')
    if Path(git(repo,'rev-parse','--show-toplevel')).resolve()!=repo: raise ValueError('Select exact repository root')
    with ProjectLock(root/'.terminal-versions.lock',timeout=5):
        state=_read(root,pid)
        if any(v['version_id']==label for v in state.get('versions',[])): raise ValueError('Version already exists')
        known={e['event_id'] for e in state['events']}
        if not evidence_event_ids or set(evidence_event_ids)-known: raise ValueError('Known evidence events required')
        # Locks for this operation and prior runner are not project content.
        refuse_filters(repo)
        dirty=git(repo,'status','--porcelain','--untracked-files=all')
        remaining=[s for s in dirty.splitlines() if s not in ('?? .terminal-versions.lock','?? .terminal-runner.lock')]
        if remaining: raise ValueError('Commit project changes before checkpoint')
        sha=git(repo,'rev-parse','HEAD');tree=git(repo,'rev-parse','HEAD^{tree}')
        ref='refs/fix-checkpoints/'+hashlib.sha256(pid.encode()).hexdigest()[:16]+'/'+label
        git(repo,'update-ref',ref,sha,'0'*len(sha))
        now=datetime.now(timezone.utc).isoformat()
        sid='SRC-CHECKPOINT-'+label
        try:
            append_mutation_set(root,'source.add',{'source_id':sid,'name':'Observed code checkpoint '+label,
                'locator':str(repo),'sha':sha,'tree':tree,'evidence_event_ids':evidence_event_ids})
            record={'checkpoint_schema':'fix-code-checkpoint/v1','version_id':label,'name':label,
                'changes':[summary],'occurred_at':now,'evidence_status':'observed','source_ids':[sid],
                'plan_ids':[],'commit_sha':sha,'tree_sha':tree,'repository':str(repo),'git_ref':ref,
                'acceptance':'candidate','evidence_event_ids':evidence_event_ids,'screenshot_status':'NOT_CAPTURED'}
            append_mutation_set(root,'version.add',record);checkpoint(root)
            return record
        except BaseException:
            # Remove only our own orphan ref. A persisted version retains its pin;
            # projection repair then proceeds through doctor/checkpoint.
            if not any(v.get('version_id')==label for v in _read(root,pid).get('versions',[])):
                git(repo,'update-ref','-d',ref,sha)
            raise



def restore(root,pid,label,destination):
    root=Path(root).resolve();destination=Path(destination).absolute()
    with ProjectLock(root/'.terminal-versions.lock',timeout=5):
        state=_read(root,pid)
        v=next((v for v in versions(state) if v['version_id']==label),None)
        if v is None: raise ValueError('Unknown checkpoint')
        repo=Path(v['repository']).resolve();parent=destination.parent.resolve(strict=True)
        destination=parent/destination.name
        if destination.exists() or destination.is_symlink(): raise ValueError('Destination must be new')
        if destination==root or root in destination.parents or destination==repo or repo in destination.parents:
            raise ValueError('Restore outside current project and memory')
        refuse_filters(repo)
        if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}',v['commit_sha']):raise ValueError('Invalid commit SHA')
        reserved={'RESTORE_CONTEXT.json','RESTORE_HANDOFF.md'}
        if {x.casefold() for x in reserved}.intersection(x.casefold() for x in git(repo,'ls-tree','--name-only',v['commit_sha']).splitlines()):
            raise ValueError('Restore receipt filename collision in checkpoint')
        if git(repo,'rev-parse',v['commit_sha']+'^{tree}')!=v['tree_sha']: raise ValueError('Code tree mismatch')
        if git(repo,'rev-parse',v['git_ref'])!=v['commit_sha']: raise ValueError('Checkpoint ref changed')
        git(repo,'worktree','add','--detach',str(destination),v['commit_sha'])
        # Do not execute any restored code or replace current journal with old journal.
        receipt={'version':label,'commit_sha':v['commit_sha'],'code_root':str(destination),
                 'memory_root':str(root),'project_id':pid,'status':'restored_unexecuted',
                 'note':'Use current memory_root for MCP/dashboard. Journal files in this code snapshot are historical.'}
        atomic_write_text(destination/'RESTORE_CONTEXT.json',json.dumps(receipt,ensure_ascii=False,indent=2))
        atomic_write_text(destination/'RESTORE_HANDOFF.md','# Restored code, current history\n\nCanonical memory: '+str(root)+'\n\nDo not use the historical journal in this checkout as current memory.\nNo dependencies or application code have been executed.\n')
        eid='EV-RESTORE-'+hashlib.sha256(str(destination).encode()).hexdigest()
        append_mutation_set(root,'event.add',{'event_id':eid,'event_type':'version_restore',
            'summary':'Restored code '+label+' into separate worktree; current memory retained',
            'evidence_status':'observed','source_ids':v['source_ids'],'restore':receipt,
            'occurred_at':datetime.now(timezone.utc).isoformat()});checkpoint(root)
        return receipt


def attach_screenshot(root,pid,label,image,capture_source,claimed_commit):
    from PIL import Image
    from io import BytesIO
    root=Path(root).resolve()
    with ProjectLock(root/'.terminal-versions.lock',timeout=5):
        state=_read(root,pid);v=next((v for v in versions(state) if v['version_id']==label),None)
        if v is None or claimed_commit!=v['commit_sha']: raise ValueError('Exact checkpoint SHA required')
        if not capture_source.strip(): raise ValueError('Capture source required')
        p=Path(image)
        data=bounded_image_bytes(p)
        with Image.open(BytesIO(data)) as im:
            if im.format not in ('PNG','JPEG') or im.width*im.height>20_000_000: raise ValueError('Unsupported image')
            fmt=im.format;size=list(im.size);im.verify()
        digest=hashlib.sha256(data).hexdigest();folder=root/'version-images';folder.mkdir(exist_ok=True)
        if folder.is_symlink(): raise ValueError('Image folder must not be symlink')
        target=folder/(digest+('.png' if fmt=='PNG' else '.jpg'))
        if target.is_symlink(): raise ValueError('Image path must not be symlink')
        if not target.exists():
            with target.open('xb') as f:f.write(data)
        if hashlib.sha256(bounded_image_bytes(target)).hexdigest()!=digest: raise ValueError('Stored image mismatch')
        sid='SRC-SCREENSHOT-'+digest+'-'+label
        if sid not in {s['source_id'] for s in state['sources']}:
            append_mutation_set(root,'source.add',{'source_id':sid,'locator':capture_source,'sha256':digest,'content_status':'reported'})
        vid='VIS-'+label+'-'+digest
        if vid not in {s['visual_id'] for s in state['visuals']}:
            append_mutation_set(root,'visual.add',{'visual_id':vid,'version_id':label,'kind':'screenshot',
                'label':'Screenshot for '+label,'uri':str(target),'sha256':digest,'dimensions':size,
                'claimed_commit':claimed_commit,'observation_status':'file_observed_build_link_reported',
                'captured_at':None,'source_ids':[sid]})
        append_mutation_set(root,'version.patch',{'version_id':label,'screenshot_status':'FILE_OBSERVED_BUILD_LINK_REPORTED','visual_id':vid})
        checkpoint(root);return {'visual_id':vid,'sha256':digest,'build_link':'reported'}


def screenshot_view(root,state,v):
    import base64
    visual=next((x for x in state.get('visuals',[]) if x['visual_id']==v.get('visual_id')),None)
    if not visual:return {'status':'NOT_CAPTURED'}
    try:
        path=Path(visual['uri']);folder=Path(root).resolve()/'version-images'
        if folder.is_symlink() or path.is_symlink() or path.resolve().parent!=folder: raise ValueError()
        data=bounded_image_bytes(path)
        if hashlib.sha256(data).hexdigest()!=visual['sha256']:raise ValueError()
        mime='image/png' if path.suffix=='.png' else 'image/jpeg'
        return {'status':'FILE_OBSERVED_BUILD_LINK_REPORTED','data_uri':'data:'+mime+';base64,'+base64.b64encode(data).decode(),'sha256':visual['sha256']}
    except (OSError,KeyError,ValueError):return {'status':'MISSING_OR_CHANGED'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--project-id',required=True)
    sub=p.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('create');c.add_argument('--repo',required=True);c.add_argument('--label',required=True);c.add_argument('--summary',required=True);c.add_argument('--evidence',action='append',required=True)
    r=sub.add_parser('restore');r.add_argument('--label',required=True);r.add_argument('--destination',required=True)
    a=sub.add_parser('screenshot');a.add_argument('--label',required=True);a.add_argument('--image',required=True);a.add_argument('--source',required=True);a.add_argument('--commit',required=True)
    sub.add_parser('list');args=p.parse_args()
    if args.cmd=='create':out=create(args.root,args.project_id,args.repo,args.label,args.summary,args.evidence)
    elif args.cmd=='restore':out=restore(args.root,args.project_id,args.label,args.destination)
    elif args.cmd=='screenshot':out=attach_screenshot(args.root,args.project_id,args.label,args.image,args.source,args.commit)
    else:out=versions(_read(args.root,args.project_id))
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
