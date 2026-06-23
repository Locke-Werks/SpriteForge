# SpriteForge — Design

A game-agnostic CLI that generates Unity 2D sprites with OpenAI's gpt-image-2,
normalizes them into clean game-ready assets, and strips every trace of metadata
before anything crosses into a game repository. It is dropped into a game root as
`./SpriteForge`; the game repo never sees an API key and never sees a raw
generation — only finished, metadata-stripped PNGs cross, via `sprite handoff`.

The style, palette, and asset taxonomy are established **per project** rather than
baked in, and the whole loop is built so **Claude Code can drive it** — including
judging generated images via its Read tool.

## Pillars

1. **Style coherence.** Independently generated assets drift. The job is to make a
   set look like one game, through a locked style reference, rigid spec prompts,
   and a normalization pass.
2. **Reproducibility and cost control.** Generation is declarative and content-
   addressed. Re-running regenerates nothing that hasn't changed, so iteration is
   cheap and output is repeatable. (gpt-image-2 has no seed; accepted outputs are
   cached instead.)
3. **Clean output.** Final sprites carry no metadata, no provenance, no API
   fingerprints. They are normal game art and nothing more.
4. **Game-agnostic + agent-operable.** No look or taxonomy is hardcoded; a project
   is scaffolded from generic templates or a preset. Commands offer `--json` so an
   agent can parse results.

## The consistency strategy (three layers)

1. **Master style reference.** One image defines the visual language: palette, line
   weight, shading, lighting, detail. Iterate it at low quality, then lock one
   high-quality master (`config/style_master.png`), recorded by `config/style.yaml`.
   Everything else is generated against this image (the edit endpoint), which holds
   style far better than prompt text alone.
2. **Spec prompts.** Prompts are written like specifications — exact palette (any
   free-form set of color roles, rendered generically so the schema isn't fixed to
   one game), exact framing, exact flat background. Magenta `#FF00FF` is the default
   key; switch per asset if a subject legitimately contains it.
3. **Normalization.** What generation can't guarantee, the post-pass does: trim to
   content, scale and anchor onto the class's fixed canvas, optional palette
   enforcement, and multi-size downscale (Lanczos for smooth art, nearest for pixel
   art).

## Background removal

Every asset is generated on a flat magenta key.
- **Chroma-key (default):** key the color to alpha by color distance with a
  feathered edge, then despill the colored halo. Cleanest edges.
- **rembg (fallback, per asset):** model-based cutout for shapes where chroma-key
  struggles or the subject contains the key color.
Both feed a final edge-cleanup pass (erode, feather, alpha threshold).

## Metadata stripping

Before any sprite is written to `out/sprites`, the image is rebuilt from raw pixel
data into a fresh buffer so the PNG encoder has no text/EXIF/ICC/provenance to
write. Every written file's chunks are then verified to be rendering-only
(`IHDR/IDAT/IEND` etc.), on write and again at handoff — nothing carrying metadata
can cross the boundary.

## Caching and cost control

- **Content-addressed cache:** the key hashes model, prompt, reference-image bytes,
  size, and quality. A hit never touches the API. Editing one asset's prompt
  regenerates only that asset.
- **Expensive vs free steps are separate:** generation hits the API; background
  removal, normalization, and packing read cached raws and can re-run for free.
- **Quality tiers:** iterate at `low`, finalize at `high`; quality is part of the
  cache key.
- **Spend tracking:** token usage per call is recorded in the cache sidecars and
  surfaced by `sprite cost`.

## What keeps it game-agnostic

- **`sprite init`** scaffolds `config/` from bundled, documented templates
  (`src/spriteforge/templates/`) or a **preset** (`src/spriteforge/presets/`:
  `flat-vector`, `pixel-art`, `hand-drawn`). `--force` overwrites; `--list-styles`
  lists presets. A preset may carry a manifest tweak (pixel-art sets
  `resample: nearest`).
- **Palette-agnostic prompts:** `render_palette()` emits whatever color roles a
  project defines, so the palette schema is never fixed to one game.
- **Generic taxonomy:** `character`, `prop`, `item`, `ui`, `fx`, `background`,
  `tile` — fully data-driven from `config/assets.yaml`.
- **`--json`** output on the working commands, for agent consumption.

## Project structure

```
SpriteForge/
  pyproject.toml            name=spriteforge, console script: sprite
  .env.example  .gitignore  README.md  AGENTS.md  HANDOFF.md  DESIGN.md
  config/
    style.yaml   assets.yaml            the active project config (style_master.png minted here)
  src/spriteforge/
    cli.py client.py cache.py config.py cost.py generate.py
    bg_remove.py postprocess.py metadata.py pack.py style.py init.py
    templates/  style.yaml assets.yaml  bundled generic scaffolding
    presets/    flat-vector.yaml pixel-art.yaml hand-drawn.yaml
  cache/   out/{raw,cut,sprites}        gitignored
  tests/
```

## Hard gpt-image-2 realities

1. **Organization Verification** is required before the model responds.
2. **No transparent backgrounds** — generate on a flat key color, remove it in post.
3. **Base64, not URLs** — decode `data[0].b64_json`.
4. **Sizes** must have both edges divisible by 16, aspect 1:3–3:1. 1024×1024 is the
   safe default; downscale in post.
5. **No seed** — consistency comes from the reference + spec prompt + normalization,
   not determinism.
6. **Provenance metadata** can be attached — strip it (done in `metadata.py`).
7. **Cost shape** — image output tokens dominate; iterate low, finalize high, cache.
