import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rows(): return [json.loads(x) for x in (ROOT/'data/tickets.jsonl').read_text().splitlines()]
def test_ticket_schema_and_splits():
    data=rows()
    assert len(data)==len({r['id'] for r in data})==len({r['text'] for r in data})==24
    assert sum(r['split']=='dev' for r in data)==12
    assert sum(r['split']=='eval' for r in data)==12
    for r in data:
        assert r['team'] in {'billing','technical','account','other'}
        assert r['frustration'] in range(4)
        assert type(r['refund_requested']) is bool
        assert type(r['review_expected']) is bool
        assert r['annotation_note']
def test_boundary_cases_present():
    data={r['id']:r for r in rows()}
    assert data['dev-negation']['refund_requested'] is False
    assert data['dev-refund']['refund_requested'] is True
    assert data['dev-mixed']['review_expected'] is True
    assert data['eval-missing']['review_expected'] is True

def test_images_have_annotations_and_supported_dimensions():
    from PIL import Image
    cases=[json.loads(x) for x in (ROOT/'data/image_cases.jsonl').read_text().splitlines()]
    assert len(cases)==6
    assert any(not c['error_present'] for c in cases)
    for c in cases:
        with Image.open(ROOT/'data'/c['image_path']) as image:
            assert image.format=='PNG'
            assert all(280<=side<=1568 for side in image.size)
        assert (c['box'] is not None)==c['error_present']
