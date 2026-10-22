"""Draw model coordinates without mutating the evidence image."""
import math
from PIL import Image, ImageDraw

def pixel_box(edges: dict[str,float], size: tuple[int,int]) -> tuple[int,int,int,int]:
    left,top,right,bottom=(edges[k] for k in ('left','top','right','bottom'))
    if not all(math.isfinite(v) and 0<=v<=1 for v in (left,top,right,bottom)) or left>=right or top>=bottom:
        raise ValueError('Box must have finite ordered normalized edges in [0,1].')
    width,height=size
    if width<=0 or height<=0: raise ValueError('Image dimensions must be positive.')
    return round(left*width),round(top*height),round(right*width),round(bottom*height)


def draw_box(image: Image.Image, edges: dict|None, *, present_probability: float, threshold: float) -> Image.Image:
    result=image.copy()
    if edges is not None and math.isfinite(present_probability) and present_probability>=threshold:
        ImageDraw.Draw(result).rectangle(pixel_box(edges,image.size),outline='#C026D3',width=4)
    return result
