"""Check the simplified writer through the installed SDK without network access."""
import json
from pathlib import Path

import httpx2
import nbformat
import pytest
from openai import OpenAI


@pytest.mark.parametrize('status,text,expected', [
    ('completed', '{"reply":"We can check the duplicate charge."}', 'ok'),
    ('incomplete', '{"reply":', 'incomplete'),
])
def test_writer_retains_response_metadata(monkeypatch, tmp_path, status, text, expected):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    monkeypatch.setenv('TYPESAFE_API_KEY', '')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setenv('COURSE_MODE', 'live')
    namespace = {}
    for cell in nbformat.read(root / 'notebooks/05_patterns.ipynb', 4).cells:
        if cell.cell_type == 'code':
            exec(compile(cell.source, 'notebook05', 'exec'), namespace)
    namespace['RUN_DIR'] = tmp_path
    assert namespace['destination'] == 'review'
    assert namespace['draft_record'] is None

    def handler(request):
        body = json.loads(request.content)
        assert body['input'] == 'Test ticket'
        assert body['text']['format']['strict'] is True
        return httpx2.Response(200, json={
            'id': 'resp_test', 'object': 'response', 'created_at': 0,
            'status': status, 'model': 'gpt-6-luna',
            'output': [{'id': 'msg_test', 'type': 'message', 'role': 'assistant',
                        'status': status, 'content': [{'type': 'output_text', 'annotations': [], 'text': text}]}],
            'usage': {'input_tokens': 20, 'output_tokens': 5, 'total_tokens': 25},
        })

    with OpenAI(api_key='unit-test-only', http_client=httpx2.Client(transport=httpx2.MockTransport(handler))) as client:
        result = namespace['draft_reply'](client, 'Test ticket', 'Draft without claiming actions.')
    assert result.status == expected
    assert result.usage['total_tokens'] == 25
    assert result.raw_response['status'] == status
