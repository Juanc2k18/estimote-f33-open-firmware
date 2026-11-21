import sys
from PIL import Image
src,out,x0,y0,x1,y1,w=sys.argv[1:8]
im=Image.open(src).convert("RGBA")
bg=Image.new("RGBA",im.size,(255,255,255,255)); bg.alpha_composite(im)
c=bg.crop((int(x0),int(y0),int(x1),int(y1))).convert("RGB")
c.thumbnail((int(w),int(w)))
c.save(out)
print(im.size, c.size)
