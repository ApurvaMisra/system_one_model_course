"""Exercise teaching logic and real SDK serialization with synthetic offline responses."""
from pathlib import Path
from types import SimpleNamespace
import json

import httpx2
import nbformat
import pytest
from openai import OpenAI
from typesafe_sdk import TypeSafeClient, RetryPolicy

ROOT = Path(__file__).resolve().parents[1]


def load_lesson(name, monkeypatch, tmp_path):
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv('TYPESAFE_API_KEY', '')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setenv('COURSE_MODE', 'live')
    namespace = {}
    for cell in nbformat.read(ROOT / 'notebooks' / name, 4).cells:
        if cell.cell_type == 'code':
            exec(compile(cell.source, name, 'exec'), namespace)
    namespace['RUN_DIR'] = tmp_path
    return namespace


def test_ranking_preserves_ties_failures_and_zero_scores(monkeypatch, tmp_path):
    lesson = load_lesson('06_reranking.ipynb', monkeypatch, tmp_path)
    passages = [{'id': str(i), 'title': str(i), 'text': 'fixture'} for i in range(5)]
    def result(score, status='ok'):
        answers = {} if score is None else {'relevance': {'score': score}}
        return SimpleNamespace(answers=answers, status=status)
    ranked = lesson['rank_passages'](passages, [result(0), result(2.5), result(None, 'error'), result(2.5)])
    assert ranked.id.tolist() == ['1', '3', '0', '2', '4']
    assert ranked.loc[2, 'score'] == 0
    assert ranked.loc[3:, 'score'].isna().all()
    assert ranked.loc[3, 'status'] == 'error'
    assert ranked.loc[4, 'status'] == 'not run'
    assert lesson['selected_passages'].empty


def test_reranking_sends_query_and_passage_without_labels(monkeypatch, tmp_path):
    lesson = load_lesson('06_reranking.ipynb', monkeypatch, tmp_path)
    seen = []
    def handler(request):
        seen.append(json.loads(request.content))
        return httpx2.Response(200, json={
            'model': 'jev-1.14.0', 'usage': {'input_tokens':20,'output_tokens':10}, 'answers': {'relevance': {
                'type': 'score', 'score': 2.5, 'confidence': 0.5,
                'legend': {'0':'none','1':'topic','2':'partial','3':'direct'},
                'probabilities': {'0':0,'1':0,'2':0.5,'3':0.5},
            }},
        })
    def client():
        return TypeSafeClient(api_key='unit-test-only', transport=httpx2.MockTransport(handler),
                              retry=RetryPolicy(max_retries=0), compression=False)
    lesson['jev_client'] = client
    lesson['can_jev'] = True
    state = {'query': 'Reset a password?', 'passage': 'Choose Forgot password.'}
    result = lesson['ask_jev']('rerank-test', state, lesson['relevance_questions'])
    assert result.answers['relevance']['score'] == 2.5
    assert seen[0]['state'] == state
    assert seen[0]['questions']['relevance']['type'] == 'score'


@pytest.mark.parametrize('status,output,expected', [
    ('completed', '{"supplier":"Northwind Studio","invoice_number":"INV-2026-014","total_due":"USD 264.00","due_date":null}', 'ok'),
    ('incomplete', '{"supplier":', 'incomplete'),
    ('completed', '{"supplier":123,"invoice_number":null,"total_due":null,"due_date":null}', 'error'),
])
def test_document_extraction_keeps_nulls_and_failure_metadata(monkeypatch, tmp_path, status, output, expected):
    lesson = load_lesson('07_structured_information.ipynb', monkeypatch, tmp_path)
    def handler(request):
        body = json.loads(request.content)
        assert body['input'] == lesson['document_text']
        assert body['text']['format']['strict'] is True
        assert body['text']['format']['schema']['additionalProperties'] is False
        return httpx2.Response(200, json={
            'id':'resp_test', 'object':'response', 'created_at':0,
            'model':'gpt-6-luna', 'status':status,
            'output':[{'id':'msg_test','type':'message','role':'assistant','status':status,
                       'content':[{'type':'output_text','annotations':[],'text':output}]}],
            'usage':{'input_tokens':30,'output_tokens':10,'total_tokens':40},
        })
    def client(**kwargs):
        return OpenAI(api_key='unit-test-only', http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
    lesson['OpenAI'] = client
    lesson['can_openai'] = True
    # require_key still checks settings; use a synthetic test key, never a real dotenv key.
    from dataclasses import replace
    lesson['settings'] = replace(lesson['settings'], openai_api_key='unit-test-only')
    record = lesson['extract_fields']('test-doc', lesson['document_text'],
                                      {'input':lesson['document_text']}, lesson['InvoiceFields'])
    assert record.status == expected
    assert record.usage['total_tokens'] == 40
    assert record.raw_response['status'] == status
    if expected == 'ok':
        assert record.answers['due_date']['value'] is None
        assert record.answers['total_due']['value'] == 'USD 264.00'
    else:
        assert record.answers == {}


def test_image_extraction_requests_include_header_and_inline_evidence(monkeypatch, tmp_path):
    lesson = load_lesson('07_structured_information.ipynb', monkeypatch, tmp_path)
    seen = []
    def jev_handler(request):
        seen.append(request)
        return httpx2.Response(200, json={'model':'jev-1.14.0','usage':{'input_tokens':100,'output_tokens':10},'answers':{}})
    with TypeSafeClient(api_key='unit-test-only', transport=httpx2.MockTransport(jev_handler),
                         retry=RetryPolicy(max_retries=0), compression=False) as client:
        record = lesson['classify_screenshot'](client, lesson['image_path'])
    assert seen[0].headers['TypeSafe-Danger-Zone-Images'] == 'true'
    assert record.status == 'incomplete'

    def openai_handler(request):
        body = json.loads(request.content)
        assert body['input'][0]['content'][1]['image_url'].startswith('data:image/png;base64,')
        assert set(body['text']['format']['schema']['required']) == {'banner_text','button_label'}
        return httpx2.Response(200, json={'id':'resp_img','object':'response','created_at':0,
            'model':'gpt-6-luna','status':'completed','output':[]})
    with OpenAI(api_key='unit-test-only', http_client=httpx2.Client(transport=httpx2.MockTransport(openai_handler))) as client:
        lesson['extraction_request'](client, lesson['image_evidence'], lesson['ScreenshotFields'])
