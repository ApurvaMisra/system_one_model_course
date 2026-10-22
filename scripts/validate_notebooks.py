#!/usr/bin/env python3
"""Validate source notebooks; optionally execute fresh kernels without rewriting sources."""
import argparse
import json
import os
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]
AUDIT='''
from course_utils.records import RunRecord
_seen_records={}
def _walk_records(value):
    if isinstance(value,RunRecord):
        _seen_records[value.config_hash]=value
    elif isinstance(value,(list,tuple)):
        for item in value: _walk_records(item)
    elif isinstance(value,dict):
        for item in value.values(): _walk_records(item)
for _name,_value in list(globals().items()):
    if not _name.startswith('_'): _walk_records(_value)
print('COURSE_AUDIT='+json.dumps({
    'mode':settings.mode,'jev_key':bool(settings.typesafe_api_key),'openai_key':bool(settings.openai_api_key),
    'records':len(_seen_records),'failed_records':sum(r.status!='ok' for r in _seen_records.values()),
    'endpoints':sorted({r.endpoint for r in _seen_records.values()})}))
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notebook-dir',type=Path,default=ROOT/'notebooks')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--offline-check',action='store_true',help='Execute non-network cells with keys explicitly blank; returns 2 for incomplete live validation.')
    parser.add_argument('--mode',choices=['live','recorded'],default='live')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'work/executed')
    args=parser.parse_args()
    paths=sorted(args.notebook_dir.glob('*.ipynb'))
    if not paths:
        print('FAIL: no notebooks found'); return 1
    failures=[]; notebooks=[]
    for path in paths:
        try:
            nb=nbformat.read(path,4); nbformat.validate(nb)
            for i,cell in enumerate(nb.cells):
                if cell.cell_type=='code':
                    compile(cell.source,f'{path.name}:cell-{i}','exec')
                    if cell.outputs or cell.execution_count is not None:
                        raise ValueError('source notebook contains saved outputs/execution counts')
            notebooks.append((path,nb))
            print('STATIC PASS',path.name,flush=True)
        except Exception as exc:
            failures.append(path.name)
            print('FAIL',path.name,type(exc).__name__,str(exc),flush=True)
    print(f'{len(paths)} notebook(s); {len(failures)} static failures',flush=True)
    if failures: return 1
    if not (args.execute or args.offline_check): return 0
    args.output_dir.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,COURSE_MODE='live' if args.offline_check else args.mode)
    env['JUPYTER_PATH']=str(Path(sys.prefix)/'share/jupyter')+os.pathsep+env.get('JUPYTER_PATH','')
    if args.offline_check: env.update(TYPESAFE_API_KEY='',OPENAI_API_KEY='')
    # Jupyter's kernel lookup occurs in this process as well as the child environment.
    os.environ['JUPYTER_PATH']=env['JUPYTER_PATH']
    reports=[]; incomplete=False
    for path,nb in notebooks:
        destination=args.output_dir/path.name
        if destination.resolve()==path.resolve():
            raise ValueError('Execution output directory must not overwrite source notebooks.')
        nb.cells.append(nbformat.v4.new_code_cell(AUDIT))
        try:
            NotebookClient(nb,kernel_name='jev-course',timeout=180,
                resources={'metadata':{'path':str(path.parent.resolve())}}).execute(env=env)
            output=''.join(o.get('text','') for o in nb.cells[-1].get('outputs',[]))
            audit=json.loads(next(line.split('=',1)[1] for line in output.splitlines() if line.startswith('COURSE_AUDIT=')))
            missing=audit['mode']=='live' and (not audit['jev_key'] or (path.name.startswith(('04','05','07')) and not audit['openai_key']))
            is_incomplete=missing or audit['failed_records']>0 or (audit['mode']=='recorded' and path.name.startswith(('00','01')))
            incomplete|=is_incomplete
            reports.append({'notebook':path.name,'execution':'completed','api_validation':'incomplete' if is_incomplete else 'completed',**audit})
            print('EXECUTED',path.name,'| API validation:',reports[-1]['api_validation'],flush=True)
        except Exception as exc:
            failures.append(path.name)
            # Avoid saving exception text that could include input secrets; keep class for diagnosis.
            reports.append({'notebook':path.name,'execution':'failed','error_type':type(exc).__name__})
            print('EXECUTION FAIL',path.name,type(exc).__name__,flush=True)
        nbformat.write(nb,destination)
    (args.output_dir/'summary.json').write_text(json.dumps(reports,indent=2)+'\n')
    if failures: return 1
    if incomplete:
        print('INCOMPLETE live API validation: offline/skipped sections or unsuccessful answers. See summary.json.'); return 2
    return 0

if __name__=='__main__': raise SystemExit(main())
