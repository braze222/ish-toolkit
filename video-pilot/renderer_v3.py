#!/usr/bin/env python3
"""Elmatrix Studio v3: more expressive visual pacing and optional neural narration.

Requires ffmpeg, ffprobe, Pillow, espeak-ng. Optional: edge-tts for online neural voices.
No assets are downloaded and no video is published.
"""
from __future__ import annotations
import hashlib, json, math, os, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

MAX_INPUT=1024*1024
MAX_OUTPUT=128*1024*1024
W,H=720,1280
BG=(10,17,34); MINT=(82,241,197); WHITE=(247,249,255); MUTED=(174,190,213)
PALE=(222,233,245); CARD=(22,37,59)
class RenderError(ValueError): pass

def canonical(data): return json.dumps(data,sort_keys=True,ensure_ascii=False).encode()
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def run(args,**kw):
    return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=kw.pop('timeout',300),**kw)
def validate(data):
    if not isinstance(data,dict) or data.get('schema')!=1: raise RenderError('Unsupported project schema')
    out={'schema':1}
    for k,limit in [('title',100),('description',4500),('script',2000)]:
        v=data.get(k)
        if not isinstance(v,str) or not v.strip() or len(v)>limit or any(ord(c)<32 and c not in '\n\t' for c in v) or '<' in v or '>' in v:
            raise RenderError('Invalid '+k)
        out[k]=v.strip()
    if not out['title'].isascii() or not out['script'].isascii(): raise RenderError('Studio v3 currently requires an English ASCII title and script')
    return out
def fingerprint(data): return hashlib.sha256(canonical(validate(data))).hexdigest()

def split_scenes(script):
    sentences=[x.strip() for x in re.split(r'(?<=[.!?])\s+',script.strip()) if x.strip()]
    groups=[]; cur=''
    for sentence in sentences:
        if cur and len(cur)+len(sentence)+1>118:
            groups.append(cur); cur=sentence
        else: cur=(cur+' '+sentence).strip()
    if cur: groups.append(cur)
    if len(groups)>8:
        step=math.ceil(len(groups)/8); groups=[' '.join(groups[i:i+step]) for i in range(0,len(groups),step)]
    return groups or [script.strip()]

def font(size,bold=False):
    candidates=(['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'] if bold else ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'])
    for p in candidates:
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()
def wrap_pixels(draw,text,fnt,width):
    lines=[]; line=''
    for word in text.split():
        test=(line+' '+word).strip()
        if line and draw.textbbox((0,0),test,font=fnt)[2]>width: lines.append(line); line=word
        else: line=test
    if line: lines.append(line)
    return lines

def visual_role(i,total,text):
    low=text.lower()
    if i==1: return 'HOOK','START HERE'
    if i==total: return 'TAKEAWAY','YOUR NEXT MOVE'
    if any(x in low for x in ('first','second','third','next','finally','step')): return 'CHECKLIST',f'POINT {i-1:02d}'
    if '?' in text: return 'QUESTION','ASK YOURSELF'
    return 'INSIGHT',f'IDEA {i-1:02d}'

def draw_scene(path,project_title,text,index,total):
    im=Image.new('RGB',(W,H)); px=im.load()
    # Deep gradient plus scene-specific luminous accent, all original artwork.
    for y in range(H):
        t=y/(H-1); c=(int(BG[0]*(1-t)+20*t),int(BG[1]*(1-t)+39*t),int(BG[2]*(1-t)+67*t))
        for x in range(W): px[x,y]=c
    d=ImageDraw.Draw(im)
    accents=[(24,91,96),(48,66,117),(76,54,104),(22,99,79),(105,72,37),(40,83,105)]
    accent=accents[(index-1)%len(accents)]
    # Vary the composition by scene role rather than repeating identical title cards.
    d.ellipse((430,-150,850,270),fill=accent)
    d.ellipse((-180,930,220,1330),fill=(17,47,67))
    d.rounded_rectangle((36,42,684,1238),radius=36,outline=(48,80,103),width=2)
    d.rounded_rectangle((64,72,656,130),radius=18,fill=(23,44,64))
    d.text((84,88),'ELMATRIX  /  FIELD NOTES',font=font(20,True),fill=MINT)
    d.text((566,88),f'{index:02d}/{total:02d}',font=font(20,True),fill=PALE)
    d.rounded_rectangle((76,158,644,164),radius=3,fill=(41,62,82))
    d.rounded_rectangle((76,158,76+int(568*index/total),164),radius=3,fill=MINT)
    role,tag=visual_role(index,total,text)
    d.text((78,208),tag,font=font(22,True),fill=MINT)
    if index==1:
        headline=project_title
        size=47
    elif role=='TAKEAWAY':
        headline='Make it count.'
        size=49
    elif role=='QUESTION':
        headline='Pause. Ask this.'
        size=46
    elif role=='CHECKLIST':
        headline=f'One thing to check'
        size=43
    else:
        headline=['Here is the useful part','Keep this in mind','Make it practical','A smarter way to do it'][(index-2)%4]
        size=42
    y=270
    for line in wrap_pixels(d,headline,font(size,True),520)[:3]:
        d.text((76,y),line,font=font(size,True),fill=WHITE); y+=int(size*1.25)
    # Large graphic motif differs by scene and adds visual rhythm.
    cy=515
    if role=='CHECKLIST':
        d.rounded_rectangle((78,cy,642,cy+104),radius=24,fill=accent)
        d.ellipse((104,cy+28,152,cy+76),outline=MINT,width=4)
        d.line((116,cy+52,128,cy+64,143,cy+39),fill=MINT,width=5)
        d.text((174,cy+31),'CHECK THIS',font=font(25,True),fill=WHITE)
    elif role=='QUESTION':
        d.rounded_rectangle((78,cy,642,cy+104),radius=24,fill=accent)
        d.text((105,cy+10),'?',font=font(74,True),fill=MINT)
        d.text((174,cy+35),'A BETTER QUESTION',font=font(23,True),fill=WHITE)
    elif role=='TAKEAWAY':
        d.rounded_rectangle((78,cy,642,cy+104),radius=24,fill=accent)
        d.text((105,cy+31),'→',font=font(36,True),fill=MINT)
        d.text((174,cy+35),'TRY THIS NEXT',font=font(23,True),fill=WHITE)
    else:
        d.rounded_rectangle((78,cy,642,cy+104),radius=24,fill=accent)
        d.ellipse((105,cy+28,153,cy+76),outline=MINT,width=4)
        d.line((117,cy+52,129,cy+64,144,cy+39),fill=MINT,width=5)
        d.text((174,cy+35),'SMALL STEP, BETTER RESULT',font=font(20,True),fill=WHITE)
    body_y=665
    d.rounded_rectangle((70,body_y-24,650,1075),radius=28,fill=CARD,outline=(48,76,99),width=2)
    body=font(30); lines=wrap_pixels(d,text,body,500); yy=body_y+15
    for line in lines:
        if yy>1010: break
        d.text((100,yy),line,font=body,fill=PALE); yy+=44
    d.text((78,1110),'USEFUL IDEAS. NO FLUFF.',font=font(20,True),fill=MINT)
    d.text((78,1152),'SAVE THIS • COME BACK WHEN YOU NEED IT',font=font(17),fill=MUTED)
    im.save(path)

def synthesize(text,wav,voice,rate,pitch,engine):
    # Prefer a neural online voice; fall back to local eSpeak only when explicitly allowed.
    if engine in ('auto','neural') and shutil.which('edge-tts'):
        mp3=wav.with_suffix('.mp3')
        try:
            run(['edge-tts','--voice',voice,'--rate',rate,'--pitch',pitch,'--text',text,'--write-media',str(mp3)],timeout=180)
            run(['ffmpeg','-nostdin','-v','error','-y','-i',str(mp3),'-ar','24000','-ac','1',str(wav)],timeout=90)
            mp3.unlink(missing_ok=True)
            return 'edge-tts:'+voice
        except (subprocess.SubprocessError,OSError):
            mp3.unlink(missing_ok=True)
            if engine=='neural': raise RenderError('Neural voice failed. Check Colab internet and try voice_engine=auto.')
    # eSpeak has a measured pace and pauses, but remains recognisably synthetic.
    rate_num=int(os.environ.get('ELMATRIX_ESPEAK_SPEED','154'))
    run(['espeak-ng','-v','en','-s',str(max(125,min(175,rate_num))),'-p','48','-g','4','-w',str(wav),'--stdin'],input=text.encode(),timeout=120)
    return 'espeak-ng:en (fallback; synthetic)'

def render(job_zip,output_zip):
    for tool in ('ffmpeg','ffprobe','espeak-ng'):
        if not shutil.which(tool): raise RenderError('Missing required tool: '+tool)
    with zipfile.ZipFile(job_zip) as z:
        entries=z.infolist()
        if len(entries)!=1 or entries[0].filename!='project.json' or entries[0].file_size>65536: raise RenderError('Job ZIP must contain only project.json (max 64 KiB)')
        data=validate(json.loads(z.read('project.json')))
    scenes=split_scenes(data['script'])
    if not 1<=len(scenes)<=8: raise RenderError('Script must produce 1–8 scenes')
    engine=os.environ.get('ELMATRIX_VOICE_ENGINE','auto').lower()
    voice=os.environ.get('ELMATRIX_NEURAL_VOICE','en-ZA-LeahNeural')
    rate=os.environ.get('ELMATRIX_VOICE_RATE','-8%')
    pitch=os.environ.get('ELMATRIX_VOICE_PITCH','+0Hz')
    with tempfile.TemporaryDirectory(prefix='elmatrix-studio-v3-') as td:
        root=Path(td); audios=[]; videos=[]
        voice_used='unknown'
        for i,narration in enumerate(scenes,1):
            wav=root/f'audio-{i:02d}.wav'; png=root/f'scene-{i:02d}.png'; mp4=root/f'segment-{i:02d}.mp4'
            draw_scene(png,data['title'],narration,i,len(scenes))
            used=synthesize(narration,wav,voice,rate,pitch,engine)
            if i==1: voice_used=used
            probe=json.loads(run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(wav)],text=True,timeout=30).stdout)
            dur=float(probe['format']['duration'])+0.25
            if dur<1 or dur>50: raise RenderError('Scene narration duration is outside safe limits')
            filt="zoompan=z='min(zoom+0.00045,1.045)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=24,format=yuv420p"
            run(['ffmpeg','-nostdin','-v','error','-y','-loop','1','-i',str(png),'-t',f'{dur:.3f}','-vf',filt,'-an','-c:v','libx264','-preset','veryfast','-crf','21','-r','24','-pix_fmt','yuv420p',str(mp4)],timeout=300)
            audios.append(wav); videos.append(mp4)
        vl=root/'videos.txt'; vl.write_text(''.join("file '"+p.as_posix()+"'\n" for p in videos))
        al=root/'audios.txt'; al.write_text(''.join("file '"+p.as_posix()+"'\n" for p in audios))
        jv=root/'joined.mp4'; ja=root/'joined.wav'; final=root/'video.mp4'
        run(['ffmpeg','-nostdin','-v','error','-y','-f','concat','-safe','0','-i',str(vl),'-c','copy',str(jv)],timeout=300)
        run(['ffmpeg','-nostdin','-v','error','-y','-f','concat','-safe','0','-i',str(al),'-c','copy',str(ja)],timeout=300)
        run(['ffmpeg','-nostdin','-v','error','-y','-i',str(jv),'-i',str(ja),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(final)],timeout=300)
        info=json.loads(run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',str(final)],text=True,timeout=30).stdout)
        streams=info['streams']; vs=next((s for s in streams if s.get('codec_type')=='video'),{})
        if vs.get('width')!=720 or vs.get('height')!=1280 or not {'video','audio'}.issubset({s.get('codec_type') for s in streams}): raise RenderError('Final MP4 failed stream/dimension verification')
        if final.stat().st_size>MAX_OUTPUT-65536: raise RenderError('Final MP4 exceeds output bundle size limit')
        manifest={'schema':1,'project_sha256':fingerprint(data),'sha256':sha(final),'duration':float(info['format']['duration']),'format':'720x1280 H.264/AAC','renderer':'elmatrix-studio-v3','scenes':len(scenes),'voice':voice_used,'voice_engine_requested':engine,'voice_note':'Neural voice requires internet; eSpeak fallback is synthetic. Listen before publishing.','visuals':'original scene-varying editorial graphics with slow motion; no external assets'}
        with zipfile.ZipFile(output_zip,'x',compression=zipfile.ZIP_STORED) as z:
            z.write(final,'video.mp4'); z.writestr('render.json',canonical(manifest))
    print(json.dumps({'status':'success','output':str(output_zip),'scenes':len(scenes),'duration_seconds':manifest['duration'],'resolution':'720x1280','voice':voice_used,'bytes':Path(output_zip).stat().st_size,'sha256':manifest['sha256']},indent=2))
def main():
    if len(sys.argv)!=3: raise SystemExit('Usage: renderer_v3.py JOB.zip RESULT.zip')
    render(sys.argv[1],sys.argv[2])
if __name__=='__main__':
    try: main()
    except (RenderError,OSError,ValueError,KeyError,zipfile.BadZipFile,subprocess.SubprocessError) as e:
        print('ELMATRIX RENDER ERROR:',e,file=sys.stderr); raise SystemExit(2)
