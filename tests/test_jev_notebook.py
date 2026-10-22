"""Offline wire-contract checks for actual notebook callbacks and installed TypeSafe SDK."""
from pathlib import Path
import json
import nbformat
import httpx2
from typesafe_sdk import TypeSafeClient, RetryPolicy

def lesson(monkeypatch,tmp_path):
    root=Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    monkeypatch.setenv('TYPESAFE_API_KEY','')
    monkeypatch.setenv('OPENAI_API_KEY','')
    monkeypatch.setenv('COURSE_MODE','live')
    namespace={}
    for cell in nbformat.read(root/'notebooks/04_openai_comparison.ipynb',4).cells:
        if cell.cell_type=='code': exec(compile(cell.source,'notebook04','exec'),namespace)
    namespace['RUN_DIR']=tmp_path
    return namespace

def test_jev_text_wire_contract(monkeypatch,tmp_path):
    ns=lesson(monkeypatch,tmp_path); seen=[]
    def handler(request):
        seen.append(json.loads(request.content))
        return httpx2.Response(200,json={'model':'jev-1.14.0','usage':{'input_tokens':60,'output_tokens':15},'answers':{
            'team':{'type':'choice','choice':'billing','probabilities':{'billing':1.0,'technical':0.0,'account':0.0,'other':0.0},'confidence':1.0},
            'frustration':{'type':'score','score':1.0,'confidence':1.0,'legend':{'0':'Neutral','1':'Mild','2':'Frustrated','3':'Angry'},'probabilities':{'0':0.0,'1':1.0,'2':0.0,'3':0.0}},
            'refund_requested':{'type':'noul','noul':0.9}}})
    with TypeSafeClient(api_key='unit-test-only',transport=httpx2.MockTransport(handler),retry=RetryPolicy(max_retries=0),compression=False) as client:
        result=ns['evaluate_ticket'](client,ns['tickets'][0],'jev-1.14.0')
    assert result.status=='ok' and result.answers['refund_requested']['noul']==0.9
    assert seen[0]['state']=={'ticket':ns['tickets'][0]['text']}
    assert seen[0]['questions']['team']['criteria']['other']
    assert 'annotation_note' not in json.dumps(seen[0])

def test_jev_image_header_and_box_contract(monkeypatch,tmp_path):
    ns=lesson(monkeypatch,tmp_path); seen=[]
    def handler(request):
        seen.append((request.headers,request.content))
        return httpx2.Response(200,json={'model':'jev-1.14.0','usage':{'input_tokens':200,'output_tokens':20},'answers':{
            'category':{'type':'choice','choice':'payment','probabilities':{'payment':1.0,'login':0.0,'service':0.0,'none':0.0},'confidence':1.0},
            'severity':{'type':'score','score':2.0,'confidence':1.0,'legend':{'0':'None','1':'Warning','2':'Task','3':'Service'},'probabilities':{'0':0.0,'1':0.0,'2':1.0,'3':0.0}},
            'error_present':{'type':'noul','noul':0.95},
            'banner':{'type':'box','box':{'left':0.045,'top':0.34375,'right':0.955,'bottom':0.546875},'confidence':0.9}}})
    with TypeSafeClient(api_key='unit-test-only',transport=httpx2.MockTransport(handler),retry=RetryPolicy(max_retries=0),compression=False) as client:
        result=ns['evaluate_image'](client,ns['image_cases'][0],'jev-1.14.0',with_box=True)
    assert result.status=='ok' and result.answers['banner']['box']['left']==0.045
    assert seen[0][0]['TypeSafe-Danger-Zone-Images']=='true'
    assert b'box' in seen[0][1]
