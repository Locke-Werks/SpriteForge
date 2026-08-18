<div align="center">

<img src="assets/spriteforge.ico" width="96" alt="SpriteForge">

# SpriteForge

**Coherent Unity 2D sprite sets from a text prompt, on the art budget of a damp napkin.**

[![license](https://img.shields.io/badge/license-GPLv3-d6262a?style=flat-square)](LICENSE)
![platform](https://img.shields.io/badge/platform-Python%203.11%2B-d6262a?style=flat-square)

</div>

---

Ask an image model for "a coin" twelve times and you get twelve coins from twelve
different universes. SpriteForge exists so that doesn't happen. You lock in *one*
style, and every sprite after that is forged to match it — same palette, same
linework, same vibe — then auto-cropped to clean transparent PNGs with zero cursed
metadata, ready to drag into Unity.

It's a command-line tool. It's also built so an AI agent (hi, Claude Code) can run
the whole thing and actually *look* at what it made. See [`AGENTS.md`](AGENTS.md).

## What it actually does

- 🎨 **Locks a style once.** You mint a single "master" reference image; every asset
  is generated *against* it. Consistency by construction, not by vibes.
- ✂️ **Cuts backgrounds for you.** Everything is generated on a hideous magenta
  backdrop that gets keyed out to clean alpha. You never see the magenta. If you do,
  file a bug and avert your eyes.
- 📐 **Normalizes like a control freak.** Trim, anchor, multi-size downscale — every
  `character` lands on the same canvas, every `item` sits where it should.
- 🧼 **Strips metadata, paranoid-style.** Output PNGs are `IHDR/IDAT/IEND` and nothing
  else. No EXIF, no C2PA, no "made by a robot" tattoo. Verified on write *and* on the
  way out the door.
- 💸 **Refuses to pay twice.** Content-addressed cache. Re-running with nothing changed
  costs exactly $0.00. Change one prompt, pay for one sprite.

## Your API key is yours

This part isn't a joke. SpriteForge talks to OpenAI, so it needs your key. That key
lives in `.env` (gitignored) and is **never** printed, logged, committed, or smuggled
into your game repo. The only things that ever cross into your game are finished
sprites and a manifest.

> ⚠️ Dropping SpriteForge into a game as `./SpriteForge`? Add `/SpriteForge/` to that
> game's `.gitignore`. Your API key is not a fun surprise for your collaborators.

## Setup

Python 3.11+ and an OpenAI key that has cleared **Organization Verification**
(gpt-image-2 will ghost you otherwise — it's not you, it's their gate).

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -e ".[dev,bg]"        # bg = the background-removal stack
cp .env.example .env              # then put your key in it
```

## The ritual

```bash
# 1. Pick a vibe (or go bespoke with the blank template):
sprite init --style flat-vector   # also: pixel-art, hand-drawn   (sprite init --list-styles)

# 2. Describe your look in config/style.yaml, then forge candidate masters:
sprite style --candidates 4       # stare at out/raw/style_candidate_*.png
sprite style --accept 2           # crown a winner -> config/style_master.png

# 3. List what you want in config/assets.yaml, then:
sprite build                      # generate -> de-magenta -> normalize -> manifest
sprite build --quality high       # once you're done iterating and feeling rich

# 4. Ship only the clean stuff into your game:
sprite handoff ../Assets/Art
```

`gpt-image-2` has no seed, so you can't reproduce exact pixels from parameters —
SpriteForge caches the ones you bless instead, which is the next best thing and
arguably more honest.

## The commands, briefly

```
sprite init      scaffold config (blank template or a preset)
sprite style     mint + lock the one master reference everything copies
sprite gen       generate assets from the manifest (cached, cheap)
sprite build     the whole pipeline in one shot
sprite process   re-cut + re-normalize cached art without spending a cent
sprite pack      emit manifest.json (+ optional atlases)
sprite handoff   copy ONLY clean sprites + manifest into your game
sprite cost      find out how much this little hobby is costing you
sprite smoke     one API call to prove everything is wired up
```

Add `--json` to basically anything if a robot is reading the output.

## Things that will bite you

- **Magenta `#FF00FF` is sacred and internal.** It's the chroma key; it must never
  appear in a real sprite. If your subject is legitimately magenta, change its
  `key_color` or switch it to `background_method: rembg`.
- **Pixel art + Lanczos = mush.** The `pixel-art` preset uses nearest-neighbour
  downscales so crisp edges stay crisp. In Unity, set Filter Mode = Point.
- **`low` vs `high` quality** is part of the cache key, so drafts and finals are
  billed separately. Iterate cheap, finalize once.

## License

GPLv3 — see [`LICENSE`](LICENSE). Make cool things, keep them free, and don't bury
this in something proprietary and pretend you wrote it. The **tool** is copyleft; the
**art you generate** is between you and OpenAI's usage terms.

---

*SpriteForge makes pictures with a large language model. It will occasionally produce
something cursed. That's showbiz. Look at your sprites before you ship them.*
