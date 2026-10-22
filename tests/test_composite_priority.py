"""Check the notebook's policy arithmetic without making API calls."""
import ast
from pathlib import Path

import nbformat
import pytest
from typesafe_sdk import Score


def priority_helpers():
    path = Path(__file__).resolve().parents[1] / 'notebooks/02_triage_workflow.ipynb'
    namespace = {'Score': Score}
    for cell in nbformat.read(path, 4).cells:
        if cell.cell_type != 'code':
            continue
        for node in ast.parse(cell.source).body:
            is_helper = isinstance(node, ast.FunctionDef) and node.name in {'normalized', 'weighted_priority'}
            is_config = isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id in {'TRIAGE_QUESTIONS', 'PRIORITY_WEIGHTS'}
                for target in node.targets
            )
            if is_helper or is_config:
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


def test_different_rubrics_are_normalized_before_weighting():
    helpers = priority_helpers()
    answers = {'severity': {'score': 1.5}, 'frustration': {'score': 1.0}, 'report_quality': {'score': 2.0}}
    assert helpers['normalized'](answers, 'severity') == 0.75
    assert helpers['normalized'](answers, 'report_quality') == pytest.approx(2 / 3)
    assert helpers['weighted_priority'](answers) == pytest.approx(2 / 3)


def test_priority_endpoints_and_missing_answers():
    helpers = priority_helpers()
    low = {name: {'score': 0} for name in helpers['TRIAGE_QUESTIONS']}
    high = {'severity': {'score': 2}, 'frustration': {'score': 2}, 'report_quality': {'score': 3}}
    assert helpers['weighted_priority'](low) == 0
    assert helpers['weighted_priority'](high) == pytest.approx(1)
    del high['report_quality']
    assert helpers['normalized'](high, 'report_quality') is None
    assert helpers['weighted_priority'](high) is None
