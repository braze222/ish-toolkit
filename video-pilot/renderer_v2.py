#!/usr/bin/env python3
"""Elmatrix Studio renderer v2: scene-based portrait videos for the Colab pilot.

Run on full Linux with ffmpeg, ffprobe, espeak-ng, and Pillow installed.
Input ZIP contains only project.json; output ZIP contains video.mp4 and render.json.
"""
from __future__ import annotations
import hashlib, json, math, os, re, shutil, subprocess, sys, tempfile, textwrap, zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

MAX_INPUT = 1024 * 1024
MAX_OUTPUT = 128 * 1024 * 1024
W, H = 720, 1280
BG = (11, 19, 38)
MINT = (77, 236, 195)
WHITE = (247, 249, 255)
MUTED = (173, 190, 214)

class RenderError(ValueError): pass

def canonical(data): return json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def run(args, **kw):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=kw.pop('timeout',300), **kw)
def validate(data):
    if not isinstance(data,dict) or data.get('schema') != 1: raise RenderError('Unsupported project schema')
    out={'schema':1}
    for k,limit in [('title',100),('description',4500),('script',2000)]:
        v=data.get(k)
        if not isinstance(v,str) or not v.strip() or len(v)>limit or any(ord(c)<32 and c not in '\n\t' for c in v) or '<' in v or '>' in v:
            raise RenderError('Invalid '+k)
        out[k]=v.strip()
    if not out['title'].isascii() or not out['script'].isascii(): raise RenderError('Studio v2 currently requires an English ASCII title and script')
    return out

def fingerprint(data): return hashlib.sha256(canonical(validate(data))).hexdigest()
def split_scenes(script):
    # Sentence-aware split, then merge very short fragments and cap scene count.
    sentences=[x.strip() for x in re.split(r'(?<=[.!?])\s+',script.strip()) if x.strip()]
    if not sentences: sentences=[script.strip()]
    groups=[]; current=''
    for s in sentences:
        if current and len(current)+len(s)+1>145:
            groups.append(current); current=s
        else: current=(current+' '+s).strip()
    if current: groups.append(current)
    # Keep a useful pace and avoid an overlong video from a long script.
    if len(groups)>8:
        merged=[]
        for i in range(0,len(groups),math.ceil(len(groups)/8)): merged.append(' '.join(groups[i:i+math.ceil(len(groups)/8)]))
        groups=merged
    return groups

def font(size,bold=False):
    candidates=(['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'] if bold else ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'])
    for p in candidates:
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def wrap_pixels(draw,text,fnt,max_width):
    words=text.split(); lines=[]; line=''
    for word in words:
        test=(line+' '+word).strip()
        if line and draw.textbbox((0,0),test,font=fnt)[2]>max_width:
            lines.append(line); line=word
        else: line=test
    if line: lines.append(line)
    return lines

def draw_scene(path, title, text, index, total, label):
    im=Image.new('RGB',(W,H)); px=im.load()
    # Subtle vertical midnight gradient, no external image assets.
    for y in range(H):
        t=y/(H-1); c=(int(BG[0]*(1-t)+22*t),int(BG[1]*(1-t)+38*t),int(BG[2]*(1-t)+65*t))
        for x in range(W): px[x,y]=c
    d=ImageDraw.Draw(im)
    # Abstract editorial shapes provide depth without pretending to be footage.
    d.ellipse((470,-130,850,250),fill=(20,53,72))
    d.ellipse((-170,930,240,1340),fill=(17,49,64))
    d.rounded_rectangle((38,46,682,1234),radius=34,outline=(49,89,111),width=2)
    d.rounded_rectangle((64,78,656,136),radius=18,fill=(24,48,65))
    d.text((86,94),label.upper(),font=font(22,True),fill=MINT)
    d.text((594,94),f'{index:02d}/{total:02d}',font=font(20,True),fill=MUTED)
    d.rounded_rectangle((76,175,644,181),radius=3,fill=(41,62,82))
    d.rounded_rectangle((76,175,76+int(568*index/total),181),radius=3,fill=MINT)
    if index==1:
        d.text((78,230),'A QUICK GUIDE',font=font(24,True),fill=MINT)
        f=font(48,True); y=300
    else:
        d.text((78,232),f'POINT {index-1}',font=font(23,True),fill=MINT)
        f=font(42,True); y=330
    lines=wrap_pixels(d,title,f,540)
    for line in lines[:4]:
        d.text((76,y),line,font=f,fill=WHITE,stroke_width=0); y+=int(f.size*1.28)
    y=max(y+38,590)
    d.rounded_rectangle((70,y-24,650,min(1085,y+390)),radius=26,fill=(22,39,61),outline=(47,75,98),width=2)
    body=font(30); lines=wrap_pixels(d,text,body,500); yy=y+16
    for line in lines:
        if yy>1020: break
        d.text((100,yy),line,font=body,fill=(231,238,248)); yy+=43
    d.text((78,1120),'SAVE THIS FOR LATER',font=font(20,True),fill=MINT)
    d.text((78,1160),'ELMATRIX  •  PRACTICAL IDEAS, CLEARLY EXPLAINED',font=font(14),fill=MUTED)
    im.save(path)

def render(job_zip, output_zip):
    for tool in ('ffmpeg','ffprobe','espeak-ng'):
        if not shutil.which(tool): raise RenderError('Missing required tool: '+tool)
    with zipfile.ZipFile(job_zip) as z:
        entries=z.infolist()
        if len(entries)!=1 or entries[0].filename!='project.json' or entries[0].file_size>65536: raise RenderError('Job ZIP must contain only project.json (max 64 KiB)')
        data=validate(json.loads(z.read('project.json')))
    scenes=split_scenes(data['script'])
    if not 1<=len(scenes)<=8: raise RenderError('Script must produce 1–8 scenes')
    with tempfile.TemporaryDirectory(prefix='elmatrix-studio-v2-') as td:
        root=Path(td); audio_files=[]; video_files=[]; durations=[]
        for i, narration in enumerate(scenes,1):
            wav=root/f'audio-{i:02d}.wav'; png=root/f'scene-{i:02d}.png'; mp4=root/f'segment-{i:02d}.mp4'
            scene_title=data['title'] if i==1 else ['The key question','What to check','Make it practical','Keep it simple','Your next step','Remember this','Put it to use'][min(i-2,6)]
            draw_scene(png,scene_title,narration,i,len(scenes),'ELMATRIX FIELD NOTES')
            run(['espeak-ng','-v','en','-s','148','-p','44','-g','3','-w',str(wav),'--stdin'],input=narration.encode(),timeout=120)
            probe=json.loads(run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(wav)],text=True,timeout=30).stdout)
            dur=float(probe['format']['duration'])+0.35
            if dur<1 or dur>45: raise RenderError('Scene narration duration is outside safe limits')
            # Each scene has a subtle slow zoom for motion; audio is muxed after all segments are assembled.
            filt=f"zoompan=z='min(zoom+0.00035,1.035)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=24,format=yuv420p"
            run(['ffmpeg','-nostdin','-v','error','-y','-loop','1','-i',str(png),'-t',f'{dur:.3f}','-vf',filt,'-an','-c:v','libx264','-preset','veryfast','-crf','22','-r','24','-pix_fmt','yuv420p',str(mp4)],timeout=300)
            audio_files.append(wav); video_files.append(mp4); durations.append(dur)
        # Concatenate compatible H.264 scenes and PCM narration, then encode final AAC audio.
        vlist=root/'videos.txt'; vlist.write_text(''.join("file '"+p.as_posix()+"'\n" for p in video_files))
        alist=root/'audios.txt'; alist.write_text(''.join("file '"+p.as_posix()+"'\n" for p in audio_files))
        joined_video=root/'joined.mp4'; joined_audio=root/'joined.wav'; final=root/'video.mp4'
        run(['ffmpeg','-nostdin','-v','error','-y','-f','concat','-safe','0','-i',str(vlist),'-c','copy',str(joined_video)],timeout=300)
        run(['ffmpeg','-nostdin','-v','error','-y','-f','concat','-safe','0','-i',str(alist),'-c','copy',str(joined_audio)],timeout=300)
        run(['ffmpeg','-nostdin','-v','error','-y','-i',str(joined_video),'-i',str(joined_audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(final)],timeout=300)
        info=json.loads(run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',str(final)],text=True,timeout=30).stdout)
        streams=info['streams']; vs=next((s for s in streams if s.get('codec_type')=='video'),{})
        if vs.get('width')!=720 or vs.get('height')!=1280 or not {'video','audio'}.issubset({s.get('codec_type') for s in streams}): raise RenderError('Final MP4 failed stream/dimension verification')
        if final.stat().st_size>MAX_OUTPUT-65536: raise RenderError('Final MP4 exceeds output bundle size limit')
        manifest={'schema':1,'project_sha256':fingerprint(data),'sha256':sha(final),'duration':float(info['format']['duration']),'format':'720x1280 H.264/AAC','renderer':'elmatrix-studio-v2','scenes':len(scenes),'voice':'espeak-ng en; synthetic, not an imitation of a person','visuals':'original designed cards with subtle motion; no external assets'}
        with zipfile.ZipFile(output_zip,'x',compression=zipfile.ZIP_STORED) as z:
            z.write(final,'video.mp4'); z.writestr('render.json',canonical(manifest))
    print(json.dumps({'status':'success','output':str(output_zip),'scenes':len(scenes),'duration_seconds':manifest['duration'],'resolution':'720x1280','bytes':Path(output_zip).stat().st_size,'sha256':manifest['sha256']},indent=2))

def main():
    if len(sys.argv)!=3: raise SystemExit('Usage: renderer_v2.py JOB.zip RESULT.zip')
    render(sys.argv[1],sys.argv[2])
if __name__=='__main__':
    try: main()
    except (RenderError, OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as e:
        print('ELMATRIX RENDER ERROR:',e,file=sys.stderr); raise SystemExit(2)
