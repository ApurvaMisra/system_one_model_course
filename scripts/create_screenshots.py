"""Regenerate the original fictional UI fixtures; no external images used."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data/screenshots'
DEST.mkdir(parents=True,exist_ok=True)
font=ImageFont.load_default(size=23)
small=ImageFont.load_default(size=17)
large=ImageFont.load_default(size=32)
rows=[]
variants=[
 ('payment','Checkout','Payment declined','Your card was not charged. Try another payment method.',True,'payment',2),
 ('login','Sign in','Sign-in failed','Incorrect password. Reset it to regain account access.',True,'login',2),
 ('service','Workspace','Service unavailable','All workspaces are offline. Please try again later.',True,'service',3),
 ('success','New request','Request submitted','Your request has been saved. You can continue working.',False,'none',0),
 ('empty','Dashboard','No requests yet','Create your first request to get started.',False,'none',0),
 ('low-contrast','Workspace','Connection warning','Some updates are delayed. You can continue working.',True,'service',1),
]
for name,page,title,body,present,category,severity in variants:
    im=Image.new('RGB',(1000,640),'#F4F6FA'); d=ImageDraw.Draw(im)
    d.rectangle((0,0,1000,70),fill='#152337')
    d.text((30,22),'NORTHSTAR / Support workspace',fill='white',font=font)
    d.text((45,110),page,fill='#152337',font=large)
    d.text((45,160),'Fictional application · Course example',fill='#526277',font=small)
    banner=(45,220,955,350)
    fill='#FEECEC' if present else '#E5F6EF'
    ink='#922323' if present else '#17634C'
    if name=='empty': fill,ink='#E5ECF5','#34465C'
    if name=='low-contrast': fill,ink='#E8EAEF','#949AA5'
    d.rounded_rectangle(banner,radius=12,fill=fill)
    d.text((70,242),title,fill=ink,font=font)
    d.text((70,294),body,fill=ink,font=small)
    d.rounded_rectangle((45,390,955,540),radius=10,fill='white',outline='#D7DFE9',width=2)
    d.text((70,412),'Request details',fill='#152337',font=font)
    d.text((70,456),'Example record 104   |   Team workspace',fill='#526277',font=small)
    d.rounded_rectangle((730,465,920,515),radius=8,fill='#236D7D')
    d.text((755,480),'Continue',fill='white',font=small)
    d.text((45,594),'Synthetic teaching fixture. No customer information.',fill='#526277',font=small)
    path=DEST/f'{name}.png'; im.save(path)
    rows.append(dict(id='image-'+name,image_path='screenshots/'+path.name,error_present=present,
                     category=category,severity=severity,
                     box={'left':.045,'top':220/640,'right':.955,'bottom':350/640} if present else None))
(ROOT/'data/image_cases.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
# Inspection contact sheet, not a model input.
contact=Image.new('RGB',(1000,960),'white')
for i,r in enumerate(rows):
    with Image.open(ROOT/'data'/r['image_path']) as im:
        contact.paste(im.resize((500,320)),((i%2)*500,(i//2)*320))
(ROOT/'work').mkdir(exist_ok=True)
contact.save(ROOT/'work/screenshots-contact.png')
