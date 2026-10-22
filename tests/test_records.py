import json
import pytest

def record(**changes):
    from course_utils.records import RunRecord
    return RunRecord(provider='openai', endpoint='decisions', requested_model='requested',
                     resolved_model='resolved', example_id='unit-fixture', config_hash='abc',
                     timestamp='2026-10-18T00:00:00+00:00', mode='live', trial=0, warmup=False,
                     status='ok', answers={'flag':{'type':'predicate','probability':0.8}},
                     answer_statuses={'flag':'ok'}, raw_response={'model':'resolved','answers':[]},
                     elapsed_ms=10, usage={'input_tokens':10,'output_tokens':0}, **changes)

def test_round_trip_and_resolved_model(tmp_path):
    from course_utils.records import save_records, load_records
    p=tmp_path/'runs.jsonl'; save_records([record()],p)
    loaded=load_records(p,'abc')[0]
    assert loaded.requested_model=='requested' and loaded.resolved_model=='resolved'
    assert loaded.answers['flag']['probability']==0.8
    assert loaded.mode=='recorded'  # Replay must not masquerade as live timing.

def test_reject_hash_mismatch(tmp_path):
    from course_utils.records import save_records, load_records
    p=tmp_path/'runs.jsonl'; save_records([record()],p)
    with pytest.raises(ValueError,match='configuration'):
        load_records(p,'different')

def test_endpoints_have_distinct_identity():
    from course_utils.records import config_hash
    assert config_hash({'endpoint':'decisions','model':'same'}) != config_hash({'endpoint':'responses','model':'same'})
    assert config_hash({'a':1,'b':2})==config_hash({'b':2,'a':1})

def test_secrets_rejected_from_recording(tmp_path):
    from course_utils.records import save_records
    r=record(); r.raw_response={'headers':{'Authorization':'Bearer sentinel-secret'}}
    with pytest.raises(ValueError,match='credential'):
        save_records([r],tmp_path/'bad.jsonl')
    assert not (tmp_path/'bad.jsonl').exists()

def test_decisions_partial_refusal():
    from course_utils.records import normalize_answers
    raw={'answers':[{'type':'predicate','name':'refund_requested','probability':0.9},
                    {'type':'refusal','name':'team'}]}
    answers,statuses,status=normalize_answers('decisions',raw,['team','refund_requested'])
    assert 'team' not in answers
    assert answers['refund_requested']['probability']==0.9
    assert statuses=={'team':'refusal','refund_requested':'ok'} and status=='partial'

def test_missing_answers_and_incomplete_responses():
    from course_utils.records import normalize_answers
    a,s,status=normalize_answers('decisions',{'answers':[]},['team'])
    assert a=={} and s['team']=='incomplete' and status=='incomplete'
    a,s,status=normalize_answers('responses',{'status':'incomplete','output':[]},['team'])
    assert status=='incomplete' and a=={}

def test_responses_normalizes_fields_without_probabilities():
    from course_utils.records import normalize_answers
    raw={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"team":"billing","frustration":1,"refund_requested":true}'}]}]}
    a,s,status=normalize_answers('responses',raw,['team','frustration','refund_requested'])
    assert a['team']=={'value':'billing'} and status=='ok'
    assert 'confidence' not in a['team']

def test_explicit_replay_never_calls_network(tmp_path):
    from course_utils.records import run_case
    called=[]
    with pytest.raises(FileNotFoundError):
        run_case(lambda:called.append(True),provider='typesafe',endpoint='systemone',model='m',
                 example_id='x',config={'input':'a'},question_names=['q'],mode='recorded',directory=tmp_path)
    assert called==[]

def test_api_failure_becomes_record(tmp_path):
    from course_utils.records import run_case
    def fail(): raise TimeoutError('network timeout')
    r=run_case(fail,provider='typesafe',endpoint='systemone',model='m',example_id='x',
               config={'input':'a'},question_names=['q'],mode='live',directory=tmp_path)
    assert r.status=='error' and r.answers=={} and r.elapsed_ms>=0
    assert r.answer_statuses['q']=='error'
