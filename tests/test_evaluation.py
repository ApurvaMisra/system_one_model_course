import pytest

def test_failed_calls_stay_in_denominator():
    from course_utils.evaluation import classification_metrics
    m=classification_metrics({'a':'billing','b':'account'},{'a':'billing'})
    assert (m['total'],m['correct'],m['failed'],m['accuracy'])==(2,1,1,0.5)
    assert m['confusion']['account']['<failed>']==1

def test_no_accepted_cases():
    from course_utils.evaluation import selective_metrics
    m=selective_metrics([True,False],[False,False])
    assert m=={'coverage':0,'review_rate':1,'accepted_accuracy':None,'accepted':0,'total':2}

def test_route_boundary_and_invalid_confidence():
    from course_utils.evaluation import route_team
    assert route_team('billing',0.7,0.7)=='billing'
    assert route_team('billing',0.69,0.7)=='review'
    assert route_team('billing',float('nan'),0.7)=='review'

def test_unknown_cost_is_not_zero():
    from course_utils.evaluation import estimate_cost
    assert estimate_cost(None,{'input':0.1,'output':0}) is None
    assert estimate_cost({'input_tokens':10},None) is None
    assert estimate_cost({'input_tokens':1000000,'output_tokens':0},{'input':0.1,'output':0})==0.1

def test_cost_accounts_for_cache_rates():
    from course_utils.evaluation import estimate_cost
    usage={'input_tokens':1000,'output_tokens':100,'input_tokens_details':{'cached_tokens':200,'cache_write_tokens':100}}
    assert estimate_cost(usage,{'input':0.1,'output':0.5,'cached_input':0.01,'cache_write':0.125})==pytest.approx(0.0001345)
    assert estimate_cost(usage,{'input':0.1,'output':0.5}) is None

def test_latency_excludes_replay_and_warmups():
    from course_utils.evaluation import latency_summary
    from course_utils.records import RunRecord
    def r(t,**kw):
        return RunRecord(provider='typesafe',endpoint='systemone',requested_model='m',example_id='x',
            config_hash='h',timestamp='t',elapsed_ms=t,**kw)
    result=latency_summary([r(10),r(999,mode='recorded'),r(999,warmup=True),r(20,status='error')])
    assert result['success']['n']==1 and result['success']['p50_ms']==10
    assert result['failure']['n']==1 and result['failure']['p50_ms']==20

def test_threshold_uses_dev_and_can_review_all():
    from course_utils.evaluation import choose_threshold
    assert choose_threshold([False,False],[0.8,0.95]) is None
    assert choose_threshold([True,False],[0.95,0.55])==0.6

def test_task_report_counts_missing_and_preserves_fractional_score():
    from course_utils.evaluation import task_report
    from course_utils.records import RunRecord
    r=RunRecord(provider='typesafe',endpoint='systemone',requested_model='m',example_id='a',config_hash='h',timestamp='t',
        answers={'team':{'choice':'billing'},'frustration':{'score':1.5},'refund_requested':{'noul':0.8}},
        answer_statuses={'team':'ok','frustration':'ok','refund_requested':'ok'})
    cases=[{'id':'a','team':'billing','frustration':1,'refund_requested':True},
           {'id':'b','team':'account','frustration':0,'refund_requested':False}]
    result=task_report(cases,[r],kind='text',rates={})
    assert result['category_accuracy']==0.5 and result['category_failed']==1
    assert result['score_mae']==0.5 and result['score_valid']==1
    assert result['brier']==pytest.approx(0.04) and result['brier_valid']==1
    assert result['cost_usd'] is None

def test_task_report_responses_has_no_invented_brier():
    from course_utils.evaluation import task_report
    from course_utils.records import RunRecord
    r=RunRecord(provider='openai',endpoint='responses',requested_model='m',example_id='i',config_hash='h',timestamp='t',
        answers={'category':{'value':'none'},'severity':{'value':0},'error_present':{'value':False}})
    result=task_report([{'id':'i','category':'none','severity':0,'error_present':False}],[r],kind='image',rates={})
    assert result['binary_accuracy']==1 and result['brier'] is None
