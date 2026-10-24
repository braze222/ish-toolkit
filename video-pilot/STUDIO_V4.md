# Elmatrix Studio v4

Studio v4 combines expressive scene graphics and neural-voice preference with burned-in synchronized captions. It also fixes audio concatenation by normalizing all synthesized scene audio to 24 kHz mono PCM before joining it.

## What changed
- Prefers `edge-tts` voice `en-ZA-LeahNeural`, with configurable rate and pitch.
- `auto` falls back to eSpeak if neural TTS fails; `neural` fails explicitly rather than silently using the fallback.
- Original scene graphics vary by scene role with subtle motion.
- Short word-group captions are timed proportionally to the actual audio duration per scene and burned into the MP4 for reliable mobile playback.
- Output metadata records actual voice engine and caption timing limitations.

## Run
1. Open [Studio v4 in Colab](https://colab.research.google.com/github/braze222/ish-toolkit/blob/feature/video-pilot/video-pilot/Colab_Studio_v4.ipynb).
2. Run setup, then render.
3. Upload one ZIP created by `prepare-cloud` containing only `project.json`.
4. Preview audio and video; check pronunciation, caption timing, safe margins and pace.
5. Download `render-result-v4.zip`, save to Files/xxix, and import into a **new project directory**.

## Voice options
- `ELMATRIX_VOICE_ENGINE='auto'`: neural voice if reachable, otherwise eSpeak fallback.
- `ELMATRIX_VOICE_ENGINE='neural'`: stop if neural TTS fails.
- `ELMATRIX_NEURAL_VOICE='en-ZA-LeahNeural'`: try `en-ZA-LukeNeural` or `en-US-JennyNeural`.
- `ELMATRIX_VOICE_RATE='-8%'`: slightly slower; try `-5%` or `-10%`.

## Known limitations
Captions are word-group timed by proportional word count, not aligned to individual phonemes; review the finished render. Neural TTS depends on internet access and an external service and remains synthetic. No external footage is fetched, no upload or publication is performed, and free Colab availability is not guaranteed. English ASCII scripts only, 1–8 scenes, 720×1280 H.264/AAC.
