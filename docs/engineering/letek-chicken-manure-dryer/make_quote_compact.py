"""Compact (base-14 font, no embedded fonts) version of the LETEK quote for e-mail delivery.
Reads quote_data.json written by make_quote.py. Output ~50 KB."""
import json, io, subprocess
from pathlib import Path
from PIL import Image
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                Image as RLImage, PageBreak, NextPageTemplate, KeepTogether)
from reportlab.lib.enums import TA_RIGHT
HERE=Path(__file__).parent; REPO=HERE.parents[2]
D=json.load(open(HERE/'quote_data.json'))
OUT=HERE/('MCE_Quote_%s_Chicken_Manure_Dryer.pdf'%D['ref'])
NAVY=colors.HexColor('#0b2a4a'); RED=colors.HexColor('#c8102e'); GREY=colors.HexColor('#555555')
def esc(t): return t.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
base=ParagraphStyle('b',fontName='Helvetica',fontSize=8.6,leading=11)
small=ParagraphStyle('s',parent=base,fontSize=7.8,leading=9.6,textColor=GREY)
h=ParagraphStyle('h',fontName='Helvetica-Bold',fontSize=11,leading=14,textColor=NAVY,spaceBefore=8,spaceAfter=3)
title=ParagraphStyle('t',fontName='Helvetica-Bold',fontSize=20,leading=24,textColor=NAVY)
right=ParagraphStyle('r',parent=base,alignment=TA_RIGHT)
# logo -> small JPEG on white
im=Image.open(REPO/'renderer'/'assets'/'mce-logo.png').convert('RGBA'); im.thumbnail((240,240))
bg=Image.new('RGB',im.size,'white'); bg.paste(im,mask=im.split()[3]); lb=io.BytesIO(); bg.save(lb,'JPEG',quality=60,optimize=True); lb.seek(0)
logo=RLImage(lb,width=1.9*inch,height=1.9*inch*im.size[1]/im.size[0])

def footer(c,doc):
    c.saveState(); c.setFont('Helvetica',7); c.setFillColor(GREY)
    c.drawString(0.6*inch,0.42*inch,'Midwest Custom Engineering, Inc.  -  6526 S Kanner Hwy #215, Stuart, FL 34997  -  usemce.com')
    c.drawRightString(doc.pagesize[0]-0.6*inch,0.42*inch,'Quote %s  -  page %d'%(D['ref'],doc.page)); c.restoreState()
doc=BaseDocTemplate(str(OUT),pagesize=letter,leftMargin=0.6*inch,rightMargin=0.6*inch,topMargin=0.55*inch,bottomMargin=0.65*inch,
                    title='MCE Quote %s - LETEK DCG'%D['ref'],author='Midwest Custom Engineering, Inc.')
W=letter[0]-1.2*inch
doc.addPageTemplates([PageTemplate('p',[Frame(0.6*inch,0.65*inch,W,letter[1]-1.2*inch,id='f')],onPage=footer),
                      PageTemplate('l',[Frame(0.4*inch,0.4*inch,landscape(letter)[0]-0.8*inch,landscape(letter)[1]-0.8*inch,id='fl')],pagesize=landscape(letter))])
S=[]
meta=Table([[logo,Paragraph('Quote',title)],['',Table([[Paragraph('Quote ref.',small),Paragraph(D['ref'],base)],[Paragraph('Issue date',small),Paragraph(D['issue_date'],base)],
      [Paragraph('Expires',small),Paragraph(D['expires'],base)],[Paragraph('Currency',small),Paragraph('USD',base)]],colWidths=[0.8*inch,1.6*inch])]],colWidths=[W-2.6*inch,2.6*inch])
meta.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,-1),(-1,-1),1.2,NAVY),('BOTTOMPADDING',(0,-1),(-1,-1),6)]))
S+= [meta,Spacer(1,6)]
party=Table([[Paragraph('<b>Seller</b>',base),Paragraph('<b>Buyer</b>',base)],
  [Paragraph('Midwest Custom Engineering, Inc.<br/>6526 S Kanner Hwy #215<br/>Stuart, FL 34997, United States<br/>Contact: Jason Shipley (jason@usemce.com), +1 620 200 9109',base),
   Paragraph('LETEK DCG<br/>Bosques de las Lomas, Mexico City, Mexico<br/>Contact: Bernardo Urquiza (burquiza@letekdcg.com)',base)]],colWidths=[W/2,W/2])
party.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')])); S+=[party,Spacer(1,4)]
S+=[Paragraph('Cover letter',h),Paragraph(esc(D['comments']),base)]
S+=[Paragraph('Line items',h)]
rows=[[Paragraph('<b>#</b>',base),Paragraph('<b>Item</b>',base),Paragraph('<b>Qty</b>',right),Paragraph('<b>Unit price</b>',right),Paragraph('<b>Net</b>',right)]]
for i,l in enumerate(D['lines'],1):
    net=l['qty']*l['unit']; opt=l['name'].startswith('OPTION')
    up='TBD' if not l['unit'] else '${:,.2f}'.format(l['unit'])
    nt='TBD' if not l['unit'] else ('${:,.2f}'.format(net)+('<br/><font size=7 color="#555555">not in total</font>' if opt else ''))
    desc='<br/>'.join(esc(x) for x in l['desc'].splitlines() if x.strip())
    rows.append([Paragraph(str(i),base),Paragraph('<b>%s</b><br/>%s'%(esc(l['name']),desc),base),Paragraph(str(l['qty']),right),Paragraph(up,right),Paragraph(nt,right)])
rows.append(['',Paragraph('<b>Subtotal</b>',right),'','',Paragraph('<b>%s</b>'%D['subtotal'],right)])
rows.append(['',Paragraph('<b>Total contract value (USD, FOB Stuart, FL)</b>',right),'','',Paragraph('<b>%s</b>'%D['subtotal'],right)])
t=Table(rows,colWidths=[0.3*inch,W-3.1*inch,0.45*inch,1.15*inch,1.2*inch],repeatRows=1)
t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),0.8,NAVY),('LINEBELOW',(0,1),(-1,-3),0.3,colors.HexColor('#cccccc')),
  ('LINEABOVE',(0,-2),(-1,-2),0.8,NAVY),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef5')),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
S+=[t,Paragraph('Terms',h),Paragraph(esc(D['terms']),base),Spacer(1,10),
    Paragraph('Accepted for LETEK DCG: ______________________________   Name: ____________________   Date: ____________',base)]
# flow sheet page (raster, landscape) - skipped when NOFLOW=1 (e-mail copy)
import os
if os.environ.get('NOFLOW')!='1':
    subprocess.run(['pdftoppm','-jpeg','-r','80','-jpegopt','quality=55','-singlefile',str(HERE/'LETEK_140tpd_caseA_Flow.pdf'),str(HERE/'_flowc')],check=True)
    fj=Image.open(HERE/'_flowc.jpg'); fb=io.BytesIO(); fj.save(fb,'JPEG',quality=55,optimize=True); fb.seek(0); (HERE/'_flowc.jpg').unlink()
    fh=landscape(letter)[1]-1.3*inch; fw=fh*fj.size[0]/fj.size[1]; S+=[NextPageTemplate('l'),PageBreak(),RLImage(fb,width=fw,height=fh)]
doc.build(S)
print('written',OUT.name,OUT.stat().st_size,'bytes')
