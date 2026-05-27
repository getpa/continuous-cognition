# Continuous Cognition Voice Agent (SGLang Prototype)

This repository contains a minimal runtime prototype for an **interruptible continuous-cognition** voice agent using SGLang-style semantics.

## What this prototype demonstrates

- One continuous cognition stream (`<thinking>...</thinking>`)
- Periodic speech externalization (`<assistant>...</assistant>`)
- In-place generation pause/resume semantics
- No prompt replay / no branch merge / no second hidden agent
- Thinking continues while TTS is playing
- Re-anchoring cognition after each speech chunk

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python continuous_cognition_runtime.py --topic "Explain momentum conservation" --chunks 4
```

## Notes

- `MockSGLangSession` models the control-plane semantics (`pause_generation(mode="in_place")`, `continue_generation()`, stop control, and in-stream injection).
- `MockTTSBackend` models async TTS playback and exposes measured playback duration, which the scheduler uses as cognition budget.
- Replace the mock classes with real SGLang + TTS providers without changing scheduler semantics.
