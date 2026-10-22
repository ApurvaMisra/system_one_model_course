import subprocess
import sys
from pathlib import Path
import nbformat
ROOT=Path(__file__).resolve().parents[1]

def test_validator_reports_syntax_error(tmp_path):
    n=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('if broken')])
    nbformat.write(n,tmp_path/'bad.ipynb')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/validate_notebooks.py'),'--notebook-dir',str(tmp_path)],capture_output=True,text=True)
    assert result.returncode==1
    assert 'SyntaxError' in result.stdout

def test_validator_accepts_clean_notebook(tmp_path):
    n=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('answer = 42')])
    nbformat.write(n,tmp_path/'good.ipynb')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/validate_notebooks.py'),'--notebook-dir',str(tmp_path)],capture_output=True,text=True)
    assert result.returncode==0 and '1 notebook' in result.stdout

def test_validator_rejects_saved_outputs(tmp_path):
    n=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('print(42)',execution_count=1,
        outputs=[nbformat.v4.new_output('stream',name='stdout',text='42')])])
    nbformat.write(n,tmp_path/'dirty.ipynb')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/validate_notebooks.py'),'--notebook-dir',str(tmp_path)],capture_output=True,text=True)
    assert result.returncode==1 and 'saved outputs' in result.stdout
