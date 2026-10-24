# Elmatrix Studio v2

Studio v2 upgrades the basic single-card draft into a scene-based portrait video: up to eight original designed cards, scene-by-scene narration, progress indicator, subtle zoom motion, a closing card, H.264/AAC output, and ZIP/hash verification. It uses synthetic English speech and original generated graphics; it does not fetch footage, use a paid AI API, or publish anything.

## Run on Google Colab

Open the notebook on the `feature/video-pilot` branch:

`https://colab.research.google.com/github/braze222/ish-toolkit/blob/feature/video-pilot/video-pilot/Colab_Studio_v2.ipynb`

Run the setup cell, then the render cell. Upload only the script-only ZIP produced by `elmatrix_video.py prepare-cloud`. Preview the result and save `render-result-v2.zip` to the iPhone Files location shared with iSH as `/mnt/xxix-share`.

## Import safely into a new project

The current importer intentionally refuses to overwrite an existing render. Preserve the original pilot and create a separate v2 project directory:

```sh
mkdir -p "$HOME/elmatrix-videos/cleaning-001-v2"
cp "$HOME/elmatrix-videos/cleaning-001/project.json" "$HOME/elmatrix-videos/cleaning-001-v2/project.json"
cd "$HOME/elmatrix-video-pilot" || exit 1
python3 video-pilot/elmatrix_video.py import-render \
  "$HOME/elmatrix-videos/cleaning-001-v2" \
  --bundle /mnt/xxix-share/render-result-v2.zip
```

After import, copy the video to a unique preview filename if desired:

```sh
cp "$HOME/elmatrix-videos/cleaning-001-v2/video.mp4" \
  /mnt/xxix-share/cleaning-001-v2-preview.mp4
```

The renderer currently supports English ASCII title/script, portrait 720×1280, and a maximum of eight scenes. Generated graphics are editorial cards, not real-world or AI-generated footage. Always preview the result before publishing. No automatic upload is implemented.
