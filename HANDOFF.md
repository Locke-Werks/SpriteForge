# SpriteForge — Handoff Guide

**Audience:** the agent/developer building the *game*. This explains how to obtain
sprites from SpriteForge and wire them into the game. You consume its finished
output; you don't need its internals.

## Layout — the tool lives at `./SpriteForge`

SpriteForge is dropped into the **root of the game project**, so it is always at
`./SpriteForge` relative to the game root:

```
your-game/                     <- the GAME repo
  SpriteForge/                 <- this tool (its OWN private git repo + its own key)
    config/assets.yaml         <- the list of sprites to make (edit this)
    config/style.yaml          <- the look
    config/style_master.png    <- the locked master (minted once per project)
    .env                       <- OpenAI key — LOCAL ONLY, never commit
    out/sprites/               <- finished art (the handoff source)
  Assets/Art/                  <- where finished sprites land (committed WITH the game)
  ... rest of the game ...
```

## ⚠️ CRITICAL: keep `SpriteForge/` out of the game repo

Because `./SpriteForge` sits inside the game project, you **must** add this line to
the **game repo's** `.gitignore`:

```gitignore
/SpriteForge/
```

`SpriteForge/` is a separate private repo with the OpenAI key in `.env`, plus a
cache and raw generations that can carry **C2PA / provenance metadata**. The game
repo must never track anything under `SpriteForge/`. The *only* thing that may
enter the game repo is finished sprites, copied into your art folder by
`sprite handoff`.

## Boundary rules (non-negotiable)

1. The game repo **gitignores `/SpriteForge/`**.
2. Never commit, print, or echo the key (`SpriteForge/.env`).
3. Only `out/sprites/` + `manifest.json` cross, and **only** via `sprite handoff` —
   never hand-copy from `cache/`, `out/raw/`, or `out/cut/`.
4. Received sprites are **final**: transparent RGBA, normalized, multi-size,
   metadata-free. Do not re-process them.

## One-time setup (inside `./SpriteForge`)

**Windows (PowerShell):**
```powershell
cd SpriteForge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,bg]"
copy .env.example .env          # then edit .env:  OPENAI_API_KEY=sk-...
sprite smoke                    # verify -> out/raw/smoke.png
```

**macOS / Linux:**
```bash
cd SpriteForge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,bg]"
cp .env.example .env            # then edit .env:  OPENAI_API_KEY=sk-...
sprite smoke
```

Requires Python 3.11+. gpt-image-2 requires OpenAI **Organization Verification**.
On first rembg use a ~176 MB model downloads once to `~/.u2net/`.

## The usage loop (run inside `./SpriteForge`)

```bash
# activate once per terminal:  source .venv/bin/activate    (mac/linux)
#                              .\.venv\Scripts\Activate.ps1  (windows)

sprite init --style flat-vector   # or `sprite init` for a blank template
# edit config/style.yaml, then mint the master:
sprite style --candidates 4       # pick one after viewing out/raw/style_candidate_*.png
sprite style --accept 2
# edit config/assets.yaml, then:
sprite build                      # iterate; only new/changed assets cost anything
sprite build --quality high       # finals
sprite handoff ../Assets/Art      # ship only clean art into the game
```

`../Assets/Art` is the same on every machine because SpriteForge sits at the game
root. Adjust it to wherever your project keeps sprites.

To request an asset without running the tool yourself, tell the operator the
**name, class, and a one-line subject** (e.g. "item_potion — class item — a small
red health potion bottle").

## What you receive

Into your art folder:

- **`{name}_{size}.png`** — clean, transparent, metadata-free RGBA sprites, square.
  Names are lower_snake_case, class-prefixed (`character_`, `item_`, `prop_`, ...).
- **`manifest.json`** — the index of the set.

Every PNG is exactly `IHDR / IDAT / IEND` — no EXIF, text, ICC, or provenance.
Verified on write and again on handoff.

### `manifest.json` schema

```json
{
  "generated_by": "spriteforge",
  "style": "Flat Vector",
  "classes": {
    "character": { "canvas": 512, "anchor": "bottom-center", "variants": [256, 128] },
    "item":      { "canvas": 256, "anchor": "center",        "variants": [128, 64] }
  },
  "sprites": [
    {
      "name": "item_coin",
      "class": "item",
      "anchor": "center",
      "sizes": [256, 128, 64],
      "files": { "256": "item_coin_256.png", "128": "item_coin_128.png", "64": "item_coin_64.png" }
    }
  ]
}
```

- `sizes` is descending; the first (== class `canvas`) is full resolution, the rest
  are clean downscales. Pick the size closest to the on-screen footprint.
- `anchor` → Unity sprite **pivot**: `center` → `(0.5, 0.5)`; `bottom-center` →
  `(0.5, 0.0)` (grounded objects like characters sit on their base).

### Unity import notes

- Import as **Sprite (2D and UI)**; alpha is transparency; no extra processing.
- Set each sprite's **pivot from the manifest `anchor`** for correct world registration.
- For pixel-art sets, set the texture **Filter Mode = Point (no filter)** and
  **Compression = None**, and disable mipmaps.
- Atlasing: let Unity's **Sprite Atlas** pack on import (simplest), or have the
  operator pre-pack (`sprite pack --atlas` → `atlas_{class}.png` + `.json`).

## Gotchas

- **Magenta is internal only.** Sprites are generated on a flat `#FF00FF` key that
  is removed in post; it must never appear in a finished sprite or in the game.
- **Sprites are pre-cut** — don't run your own background removal; they're already
  clean transparent RGBA.
- **Re-runs are free** — building with nothing changed costs `$0` (content-addressed
  cache).
- **Style is locked** to `config/style_master.png`; the set is coherent by
  construction. For a *different* look, re-run `sprite style` (or `sprite init
  --style ...`) and rebuild.
- **gpt-image-2 has no seed** — exact pixels can't be reproduced from parameters;
  the tool caches accepted outputs instead, which is what makes re-runs reproducible.
