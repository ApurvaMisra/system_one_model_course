from pathlib import Path
import ast
import nbformat

def policy():
    path=Path(__file__).resolve().parents[1]/'notebooks/02_triage_workflow.ipynb'
    ns={}
    from course_utils.evaluation import route_team
    ns['route_team']=route_team
    for cell in nbformat.read(path,4).cells:
        if cell.cell_type=='code':
            tree=ast.parse(cell.source)
            for node in tree.body:
                if isinstance(node,ast.FunctionDef) and node.name=='triage':
                    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
    return ns['triage']

def test_failed_or_uncertain_goes_to_review():
    fn=policy()
    assert fn({},0.7)['review'] is True
    assert fn({'team':{'choice':'billing','confidence':0.6}},0.7)['team']=='review'

def test_refund_flag_is_not_refund_authorization():
    result=policy()({'team':{'choice':'billing','confidence':0.9},'refund_requested':{'noul':0.99}},0.7)
    assert result=={'team':'billing','review':False,'priority':'normal'}
