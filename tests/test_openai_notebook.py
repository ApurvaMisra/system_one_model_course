"""Run notebook-defined API calls through the real SDK and an offline HTTP transport."""
from pathlib import Path
import json
import nbformat
import pytest
import httpx2
from openai import OpenAI

def load_lesson(monkeypatch,tmp_path):
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

@pytest.fixture
def lesson(monkeypatch,tmp_path):
    return load_lesson(monkeypatch,tmp_path)

def test_decisions_text_contract(lesson):
    requests=[]
    def handler(request):
        body=json.loads(request.content); requests.append(body)
        return httpx2.Response(200,json={'model':'gpt-6-luna','usage':{'input_tokens':20,'output_tokens':0,'total_tokens':20},
            'answers':[{'name':'team','type':'choice','choice':'billing','probabilities':[{'value':'billing','probability':1.0}],'confidence':1.0},
                       {'name':'frustration','type':'score','score':1.0,'probabilities':[{'value':1,'label':'Mild','probability':1.0}],'confidence':1.0},
                       {'name':'refund_requested','type':'predicate','probability':0.95}]})
    with OpenAI(api_key='unit-test-only',http_client=httpx2.Client(transport=httpx2.MockTransport(handler))) as client:
        result=lesson['evaluate_openai'](client,lesson['tickets'][0],'decisions')
    assert result.status=='ok' and result.answers['team']['choice']=='billing'
    assert [q['type'] for q in requests[0]['questions']]==['choice','score','predicate']
    assert 'annotation_note' not in json.dumps(requests[0])
    assert 'split' not in json.dumps(requests[0])

def test_decisions_image_contract(lesson):
    requests=[]
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx2.Response(200,json={'model':'gpt-6-luna','usage':{'input_tokens':100,'output_tokens':0,'total_tokens':100},'answers':[]})
    with OpenAI(api_key='unit-test-only',http_client=httpx2.Client(transport=httpx2.MockTransport(handler))) as client:
        result=lesson['evaluate_openai'](client,lesson['image_cases'][0],'decisions',kind='image')
    parts=requests[0]['input'][0]['content']
    assert any(p.get('image_url','').startswith('data:image/png;base64,') for p in parts)
    assert 'box' not in json.dumps(requests[0]['questions'])
    assert result.status=='incomplete'

def test_responses_contract_and_parse(lesson):
    requests=[]
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx2.Response(200,json={'id':'resp_unit','object':'response','created_at':0,'status':'completed',
            'model':'gpt-6-luna','parallel_tool_calls':False,'tools':[],'tool_choice':'auto',
            'output':[{'id':'msg_unit','type':'message','role':'assistant','status':'completed',
                       'content':[{'type':'output_text','annotations':[],'text':'{"team":"billing","frustration":1,"refund_requested":true}'}]}],
            'usage':{'input_tokens':50,'output_tokens':10,'total_tokens':60}})
    with OpenAI(api_key='unit-test-only',http_client=httpx2.Client(transport=httpx2.MockTransport(handler))) as client:
        result=lesson['evaluate_openai'](client,lesson['tickets'][0],'responses')
    assert result.status=='ok' and result.answers['refund_requested']=={'value':True}
    assert requests[0]['text']['format']['type']=='json_schema'
    assert requests[0]['text']['format']['strict'] is True
    assert requests[0]['reasoning']=={'effort':'none'}


def test_lesson_ignores_dotenv_credentials(monkeypatch,tmp_path):
    import course_utils.config as config
    dotenv=tmp_path/'.env'
    dotenv.write_text('TYPESAFE_API_KEY=test-jev\nOPENAI_API_KEY=test-openai\n')
    original=config.dotenv_values
    monkeypatch.setattr(config,'dotenv_values',lambda *a,**k:original(dotenv))
    def deny(*a,**k):
        raise AssertionError('Notebook attempted to construct a live client')
    import typesafe_sdk
    monkeypatch.setattr(typesafe_sdk,'TypeSafeClient',deny)
    monkeypatch.setattr('openai.OpenAI',deny)
    namespace=load_lesson(monkeypatch,tmp_path/'runs')
    assert not namespace['can_openai'] and not namespace['can_jev']


def test_incomplete_response_retains_provenance(lesson):
    def handler(request):
        return httpx2.Response(200,json={'id':'resp_short','object':'response','created_at':0,
            'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'},
            'model':'gpt-6-luna','parallel_tool_calls':False,'tools':[],'tool_choice':'auto',
            'output':[{'id':'msg_short','type':'message','role':'assistant','status':'incomplete',
                       'content':[{'type':'output_text','annotations':[],'text':'{"team":'}]}],
            'usage':{'input_tokens':50,'output_tokens':2,'total_tokens':52}})
    with OpenAI(api_key='unit-test-only',http_client=httpx2.Client(transport=httpx2.MockTransport(handler))) as client:
        result=lesson['evaluate_openai'](client,lesson['tickets'][0],'responses')
    assert result.status=='incomplete'
    assert result.resolved_model=='gpt-6-luna'
    assert result.usage['total_tokens']==52
    assert result.raw_response['incomplete_details']['reason']=='max_output_tokens'
