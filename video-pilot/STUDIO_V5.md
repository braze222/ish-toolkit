# Elmatrix Studio v5 — Story-driven video renderer

Studio v5 adds a rule-based storyboard planner to Studio v4. It works locally in the Colab runtime and does not need a separate LLM API.

## Story planning
- Plans a hook, context, practical steps, objection/mistake beat when script wording indicates one, and a takeaway.
- Chooses visual directions for `cleaning`, `education`, `software`, or `general`.
- Includes the selected scene roles and visual prompts in `render.json`.

Add an optional `"niche": "cleaning"` (or `education`, `software`, `general`) to `project.json`. Without it, general prompts are used.

## Optional scene images
You can supply AI-generated or licensed still images yourself. Include them in the job ZIP alongside `project.json` using paths `assets/scene-01.png` through `assets/scene-08.jpg`. Valid PNG/JPEG only, 256–4096 pixels per side, max 8 MiB each and 32 MiB total job content. A dark overlay is applied for text legibility; missing images use original generated graphics. No image API is called and no media is downloaded. Ensure you have rights to any included image.

## Run
Open [Studio v5 in Colab](https://colab.research.google.com/github/braze222/ish-toolkit/blob/feature/video-pilot/video-pilot/Colab_Studio_v5.ipynb), run setup, then render. Upload one ZIP created by `prepare-cloud`, optionally extended with scene images. Review caption timing, narration, and image rights before publishing.

## Limits
English ASCII title/script; 1–8 scenes; 720×1280 H.264/AAC. Neural voice is synthetic, depends on internet and an external service. Captions are timed by proportional word count per scene, not forced alignment. No YouTube upload/publication.
