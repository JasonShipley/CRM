# Stamp MCE header/footer on every page. usage: stamp.py src.pdf out.pdf logo.png TITLE SUB REF
import sys, fitz
src, out, logo, title, sub, ref = sys.argv[1:7]
d = fitz.open(src)
BLACK=(0.07,0.07,0.07); OR=(0.95,0.45,0.1); GRAY=(0.45,0.45,0.45)
n=len(d)
for i,p in enumerate(d):
    W,H=p.rect.width,p.rect.height
    p.draw_rect(fitz.Rect(0,0,W,62),color=None,fill=BLACK)
    p.draw_rect(fitz.Rect(0,62,W,66),color=None,fill=OR)
    p.insert_image(fitz.Rect(30,8,165,53),filename=logo)
    def rtext(y,txt,size,color,bold=True):
        f="hebo" if bold else "helv"
        w=fitz.get_text_length(txt,fontname=f,fontsize=size)
        p.insert_text((W-30-w,y),txt,fontname=f,fontsize=size,color=color)
    rtext(30,title,15,(1,1,1)); rtext(43,sub,6.5,OR); rtext(54,f"{ref} · Page {i+1} of {n}",5.5,(0.85,0.85,0.85),False)
    p.draw_line((30,H-30),(46,H-30),color=OR,width=1.5)
    p.insert_text((50,H-27.5),"MIDWEST CUSTOM ENGINEERING",fontname="hebo",fontsize=5.5,color=GRAY)
    p.insert_text((50+fitz.get_text_length("MIDWEST CUSTOM ENGINEERING ",fontname="hebo",fontsize=5.5),H-27.5),"PRECISION. QUALITY. INTEGRITY.",fontname="helv",fontsize=5.5,color=GRAY)
    t="Stuart, FL · 772-200-4060 · midwestcustomengineering.com"
    p.insert_text((W-30-fitz.get_text_length(t,fontname="helv",fontsize=5.5),H-27.5),t,fontname="helv",fontsize=5.5,color=GRAY)
d.save(out, garbage=3, deflate=True)
