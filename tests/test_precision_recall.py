import pytest
from course_utils.evaluation import binary_threshold_metrics, select_binary_threshold


def test_threshold_changes_false_positives_and_misses():
    labels = [True, True, True, False, False, False]
    probabilities = [0.9, 0.6, 0.3, 0.8, 0.4, 0.1]
    low = binary_threshold_metrics(labels, probabilities, 0.3)
    high = binary_threshold_metrics(labels, probabilities, 0.9)
    assert (low['tp'], low['fp'], low['fn'], low['tn']) == (3, 2, 0, 1)
    assert low['precision'] == pytest.approx(0.6)
    assert low['recall'] == 1
    assert high['precision'] == 1
    assert high['recall'] == pytest.approx(1 / 3)
    rows = [low, binary_threshold_metrics(labels, probabilities, 0.5), high]
    assert select_binary_threshold(rows, prioritize='precision', target=0.9) == 0.9
    assert select_binary_threshold(rows, prioritize='recall', target=0.9) == 0.3


def test_undefined_metrics_and_missing_probabilities_are_explicit():
    missing = binary_threshold_metrics([True, False, True], [None, float('nan'), 0.8], 0.5)
    assert missing['missing'] == 2
    assert missing['unscored_positives'] == 1
    assert missing['coverage'] == pytest.approx(1 / 3)
    assert select_binary_threshold([missing], prioritize='recall', target=0.9) is None
    no_flags = binary_threshold_metrics([True, False], [0.1, 0.2], 0.9)
    assert no_flags['precision'] is None and no_flags['recall'] == 0
    no_positives = binary_threshold_metrics([False], [0.8], 0.5)
    assert no_positives['recall'] is None
    assert select_binary_threshold([no_positives], prioritize='recall', target=0.9) is None
    assert select_binary_threshold([], prioritize='precision', target=0.9) is None


def test_invalid_inputs_do_not_turn_into_negative_predictions():
    result = binary_threshold_metrics([True] * 4, [-0.1, 1.1, float('inf'), True], 0.5)
    assert result['missing'] == 4 and result['fn'] == 0
    with pytest.raises(ValueError):
        binary_threshold_metrics([True], [], 0.5)
    with pytest.raises(ValueError):
        binary_threshold_metrics([True], [0.5], 1.1)


def test_notebook_freezes_development_thresholds_before_heldout_report():
    from pathlib import Path
    from types import SimpleNamespace
    import nbformat
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')

    labels = [True, True, True, False, False, False]
    tickets = [{'id': str(i), 'refund_requested': label} for i, label in enumerate(labels)]
    def records(probabilities):
        return [SimpleNamespace(example_id=str(i), answers={'refund_requested': {'noul': p}})
                for i, p in enumerate(probabilities)]
    namespace = {
        'pd': pd, 'display': lambda value: None,
        'development_tickets': tickets, 'evaluation_tickets': tickets,
        'development_results': records([0.9, 0.6, 0.3, 0.8, 0.4, 0.1]),
        'evaluation_results': records([0.1, 0.2, 0.3, 0.95, 0.96, 0.97]),
    }
    path = Path(__file__).resolve().parents[1] / 'notebooks/02_triage_workflow.ipynb'
    in_section = False
    for cell in nbformat.read(path, 4).cells:
        if cell.cell_type == 'markdown' and cell.source.startswith('## Precision versus recall:'):
            in_section = True
        if cell.cell_type == 'markdown' and cell.source.startswith('## When a second call'):
            break
        if in_section and cell.cell_type == 'code':
            exec(compile(cell.source, 'refund-threshold-section', 'exec'), namespace)
    assert namespace['refund_policies']['Find requests for human review'] == 0.3
    assert namespace['refund_policies']['Expensive specialist workflow'] == 0.9
    reports = namespace['refund_policy_report']
    assert reports[1]['precision'] == 0
    assert reports[0]['recall'] == pytest.approx(1 / 3)
    import matplotlib.pyplot as plt
    plt.close('all')
