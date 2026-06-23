# SpriteForge — guide for Claude Code (the agent operating this tool)

You (Claude Code) drive SpriteForge to generate a game's Unity 2D sprites. This
is the operating manual. The human may just say "make me a coin" — your job is to
run the loop below, **look at the images you generate**, iterate until they're
right, then hand off clean art.

## What this tool is

A CLI (`sprite`) that turns a declarative config into a coherent, metadata-free
sprite set anchored to one locked style master. You establish the look once, then
every asset is generated to match it. Re-runs are content-addressed and cached
(free), so iteration is cheap.

## Boundary rules (never break these)

1. The OpenAI key lives only in `./.env` (gitignored). Never print, echo, log, or
   commit it; never copy it elsewhere.
2. When SpriteForge is dropped into a game repo as `./SpriteForge`, the **game
   repo must gitignore `/SpriteForge/`**.
3. Only `out/sprites/` + `manifest.json` may cross into the game — and only
   through `sprite handoff`. Never hand-copy from `cache/`, `out/raw/`, or `out/cut/`.

## You can see the images — use that

Claude Code's Read tool renders PNGs. This is the heart of the loop: after any
generation, **Read the PNGs and judge them yourself** before spending more.
- style candidates: `out/raw/style_candidate_*.png`
- per-asset raws (pre-cleanup): `out/raw/<name>.png`
- finished sprites: `out/sprites/<name>_<size>.png`

## The loop

1. **Scaffold** (once per project):
   `sprite init` (generic) or `sprite init --style flat-vector` (also `pixel-art`,
   `hand-drawn`; `sprite init --list-styles`).
2. **Author the style** — edit `config/style.yaml`: the `style` descriptors, the
   `palette` (free-form color roles; keep a `primary`), and `master.subject` (one
   representative subject, often the player character).
3. **Mint the master**:
   - `sprite style --candidates 4 --json` → note the `candidates[].path` list.
   - **Read each candidate PNG.** Pick the one that best matches the intended look.
   - `sprite style --accept N` → locks `config/style_master.png`.
   - If none are good, refine `config/style.yaml` and roll again.
4. **Define assets** — edit `config/assets.yaml`: add entries `{name, class,
   prompt}`. `name` is lower_snake_case, class-prefixed (e.g. `item_coin`). Use the
   closest existing class, or add one (canvas / anchor / variants).
5. **Build** (cheap iteration):
   - `sprite build --json` → generate + bg-remove + normalize + manifest. Only
     new/changed assets cost anything.
   - **Read `out/sprites/<name>_<largest>.png`** for each new asset. If a sprite is
     wrong, refine that asset's `prompt` and re-run `sprite build` (only that asset
     regenerates).
6. **Finalize**: `sprite build --quality high` for finals.
7. **Hand off**: `sprite handoff <game>/Assets/Art --json`.

## Tips

- `--json` is available on `init`, `style`, `gen`, `build`, `process`, `pack`,
  `handoff`, `cost` — use it for parseable paths, statuses, tokens, and est. USD.
- Cost: iterate at the default `low` quality; use `--quality high` only for finals.
  `sprite cost --json` shows cumulative spend. A fully-cached `build` is free.
- Background trouble (halos, or a subject that legitimately contains magenta): set
  `background_method: rembg` on that asset, or change its `key_color`.
- Pixel art: the `pixel-art` preset sets `resample: nearest`. For per-asset needs,
  set `resample` on the asset or in `defaults`.
- No API key is needed for `init`, `process`, `pack`, `cost`, `--help`, or a
  fully-cached `build`.
