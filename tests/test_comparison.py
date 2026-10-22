from types import SimpleNamespace
from course_utils.comparison import comparison_tables


def test_probabilities_stay_native_and_missing_is_not_zero():
    def record(endpoint, answers, status='ok'):
        return SimpleNamespace(endpoint=endpoint, answers=answers, status=status, error=None)
    runs = {
        'old': record('systemone', {'team': {'choice':'billing','probabilities':{'billing':0.7}}, 'refund_requested':{'noul':0.8}}),
        'new': record('systemone', {'team': {'choice':'billing','probabilities':{'billing':0.9}}}),
        'decisions': record('decisions', {'team':{'choice':'billing','probabilities':[{'value':'billing','probability':0.6}]}}),
        'llm': record('responses', {'team':{'value':'billing'},'refund_requested':{'value':True}}),
        'failed': record('systemone', {}, 'error'),
    }
    answers, probabilities = comparison_tables(runs)
    assert probabilities.loc[('team','billing'),'old']==0.7
    assert probabilities.loc[('team','billing'),'new']==0.9
    assert probabilities.loc[('team','billing'),'decisions']==0.6
    assert probabilities['llm'].isna().all()
    assert probabilities['failed'].isna().all()
    assert answers.loc['llm','team']=='billing'
    assert probabilities.loc[('refund_requested','yes'),'old']==0.8
