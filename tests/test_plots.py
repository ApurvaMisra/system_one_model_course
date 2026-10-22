import pytest
from PIL import Image

def test_pixel_box():
    from course_utils.plots import pixel_box
    assert pixel_box({'left':0.1,'right':0.8,'top':0.2,'bottom':0.5},(100,200))==(10,40,80,100)

@pytest.mark.parametrize('change',[{'left':0.9},{'top':float('nan')},{'right':1.1}])
def test_invalid_geometry(change):
    from course_utils.plots import pixel_box
    with pytest.raises(ValueError):
        pixel_box({'left':0.1,'right':0.8,'top':0.2,'bottom':0.5,**change},(100,200))

def test_absent_target_and_immutable_source():
    from course_utils.plots import draw_box
    source=Image.new('RGB',(100,200),'white'); original=source.tobytes()
    box={'left':0.1,'right':0.8,'top':0.2,'bottom':0.5}
    assert draw_box(source,box,present_probability=0.1,threshold=0.8).tobytes()==original
    assert draw_box(source,box,present_probability=0.9,threshold=0.8).tobytes()!=original
    assert source.tobytes()==original
