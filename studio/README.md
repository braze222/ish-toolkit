# Elmatrix Studio — UI foundation

This directory begins the browser-based Studio experience alongside the existing iSH Toolkit and Elmatrix CLI. It is a **front-end prototype**: it demonstrates navigation and Quick Create interaction, but does not yet call an AI provider, render a real video, persist jobs to a server, or publish to Facebook.

## Preview

Open `index.html` in a modern browser, or serve this folder with any static HTTP server. No build tools or API keys are required for the prototype.

## Next implementation steps

1. Convert the UI to React + TypeScript + Vite and add component/unit tests.
2. Add a typed API and database-backed job state machine.
3. Implement provider adapters with live health/quota checks and a zero-paid-spend default.
4. Add isolated rendering workers and output validation.
5. Add official Meta OAuth/publishing only after permissions and API support are verified.

See [../docs/ELMATRIX_STUDIO.md](../docs/ELMATRIX_STUDIO.md) for requirements, architecture, security rules, and acceptance gates.

**Free-first honesty:** a free model license does not guarantee free hosted inference. The app must never silently spend money, claim a generation succeeded when it did not, or promise channel growth.
