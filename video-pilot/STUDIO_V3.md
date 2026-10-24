# Elmatrix Studio v3

Studio v3 focuses on two improvements:

- **More human narration:** tries a neural South African English voice via `edge-tts` (`en-ZA-LeahNeural`) with a slightly slower delivery. The notebook can switch to `en-ZA-LukeNeural` or `en-US-JennyNeural`, change rate, and choose `auto` or `neural`. Neural synthesis requires internet access and a third-party online TTS service. Availability, terms, voice names, and network access may change. The renderer records the actual engine in `render.json`.
- **More creative scenes:** changes the graphic motif and composition based on the scene role, varies accent colours, gives hooks/questions/checklists/takeaways different visual treatments, and adds gentle camera motion. It still uses designed graphics rather than pretending to have real footage.

## Run it

1. Open the [Studio v3 Colab notebook](https://colab.research.google.com/github/braze222/ish-toolkit/blob/feature/video-pilot/video-pilot/Colab_Studio_v3.ipynb).
2. Run the setup cell, then the render cell.
3. Upload a ZIP produced by `prepare-cloud` containing only `project.json`.
4. Preview the video and check voice pronunciation, timing, pacing, and visual legibility.
5. Download `render-result-v3.zip`, save it in Files/xxix, and import it into a **new** project directory.

## Voice controls

In the notebook render cell:
- `ELMATRIX_VOICE_ENGINE='auto'`: use neural voice if reachable, otherwise use eSpeak fallback.
- `ELMATRIX_VOICE_ENGINE='neural'`: fail instead of silently falling back if neural voice fails.
- `ELMATRIX_NEURAL_VOICE='en-ZA-LeahNeural'`: suggested South African English voice; alternatives are listed in the notebook.
- `ELMATRIX_VOICE_RATE='-8%'`: slower, less rushed delivery. Try `-5%` or `-10%`.

A neural voice is generally more natural than eSpeak, but it is still synthetic speech, not a human recording. If the metadata says `espeak-ng`, the online voice was not used. Never claim narration is human-recorded unless it actually is.

## Limits

- English ASCII scripts only; 1–8 scenes.
- 720×1280 MP4, H.264/AAC.
- Original generated graphic cards; no stock footage or external image assets.
- No automatic YouTube upload, monetization, or publication.
- Free Colab capacity and external voice service availability are not guaranteed.
