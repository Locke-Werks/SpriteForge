"""Command-line entry points for SpriteForge (the `sprite` command).

A game-agnostic pipeline: `init` scaffolds a project's style + asset config,
`style` mints the locked master reference, `gen`/`build` generate sprites against
it, `process`/`pack` normalize and index them, and `handoff` copies only clean
finals into a Unity project. Most commands accept `--json` so Claude Code can
parse results instead of scraping human-readable text.
"""
from __future__ import annotations

import json

import typer

from . import config

app = typer.Typer(add_completion=False, help="SpriteForge — generate, normalize, and clean Unity 2D sprites.")


@app.callback()
def main() -> None:
    """SpriteForge — generate, normalize, and metadata-strip 2D game sprites."""
    # Forces Typer into multi-command mode so each command keeps its name
    # (e.g. `sprite build`).


@app.command()
def init(
    style: str = typer.Option("", "--style", help="Start from a bundled preset instead of the generic template."),
    list_styles: bool = typer.Option(False, "--list-styles", help="List bundled style presets and exit."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config/ files."),
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON summary."),
) -> None:
    """Scaffold config/ (style + assets) from the generic template or a preset."""
    from . import init as init_mod

    if list_styles:
        names = init_mod.list_presets()
        if json_out:
            typer.echo(json.dumps({"presets": names}))
        else:
            typer.echo("Bundled style presets:")
            for n in names:
                typer.echo(f"  - {n}")
            typer.echo("\nUse:  sprite init --style <name>   (or `sprite init` for the generic template)")
        return

    result = init_mod.scaffold(style=style or None, force=force)
    if json_out:
        typer.echo(json.dumps(result))
        return

    typer.echo(f"Initialized from: {result['style']}")
    for n in result["written"]:
        typer.echo(f"  + config/{n}")
    for n in result["skipped"]:
        typer.echo(f"  · config/{n} (exists; pass --force to overwrite)")
    typer.echo(
        "\nNext:\n"
        "  1. edit config/style.yaml  (the look + master.subject)\n"
        "  2. sprite style --candidates 4   then read out/raw/style_candidate_*.png\n"
        "  3. sprite style --accept N        (locks config/style_master.png)\n"
        "  4. edit config/assets.yaml  (your asset list)\n"
        "  5. sprite build                   then read out/sprites/ and iterate"
    )


@app.command()
def smoke(
    quality: str = typer.Option("low", help="low|medium|high. Keep low for the smoke test."),
    out: str = typer.Option("", help="Output path. Default: out/raw/smoke.png."),
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON summary."),
) -> None:
    """Generate one image, decode the base64, and save a PNG (a single round trip)."""
    # Imported lazily so `sprite smoke --help` needs no API key.
    from .client import ImageClient

    out_path = out or str(config.RAW_DIR / "smoke.png")
    prompt = (
        "A simple flat 2D game sprite of a single gold coin, clean vector style, "
        "soft cel shading, centered with generous margin, no text, no border. "
        f"Background: solid flat {config.DEFAULT_KEY_COLOR} magenta, completely "
        "uniform, no gradient, no texture, filling the entire canvas."
    )

    if not json_out:
        typer.echo(f"model={config.MODEL}  size={config.DEFAULT_SIZE}  quality={quality}")
        typer.echo("Calling gpt-image-2 ...")

    client = ImageClient()
    result = client.generate(prompt, quality=quality)
    saved = result.save(out_path)

    if json_out:
        typer.echo(json.dumps({
            "model": config.MODEL, "size": config.DEFAULT_SIZE, "quality": quality,
            "out": str(saved), "bytes": len(result.png_bytes), "usage": result.usage,
        }))
        return
    typer.echo(f"Saved {len(result.png_bytes):,} bytes -> {saved}")
    if result.usage:
        typer.echo(f"Token usage: {result.usage}")


@app.command()
def style(
    lock: bool = typer.Option(False, "--lock", help="Generate one final high-quality master into config/."),
    candidates: int = typer.Option(0, "--candidates", help="Roll N high-quality master candidates into out/raw/ to choose from."),
    accept: int = typer.Option(0, "--accept", help="Promote candidate N to config/style_master.png as the locked master."),
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON summary."),
) -> None:
    """Generate and iterate the master style reference, then lock it."""
    from . import style as style_mod

    if accept:
        dest = style_mod.accept_candidate(accept)
        if json_out:
            typer.echo(json.dumps({"action": "accept", "candidate": accept, "master": str(dest)}))
        else:
            typer.echo(f"Locked master <- candidate {accept}: {dest}")
        return

    if candidates:
        rolled = []
        total = 0
        for i, (result, dest) in enumerate(style_mod.generate_candidates(candidates), 1):
            tokens = (result.usage or {}).get("total_tokens")
            total += tokens or 0
            rolled.append({"index": i, "path": str(dest), "bytes": len(result.png_bytes), "tokens": tokens})
            if not json_out:
                typer.echo(f"  candidate {i}: {len(result.png_bytes):,} bytes -> {dest}  ({tokens} tokens)")
        if json_out:
            typer.echo(json.dumps({"action": "candidates", "count": candidates, "candidates": rolled, "total_tokens": total}))
            return
        typer.echo(f"Total tokens: {total}. Read the candidate PNGs, then run `sprite style --accept N`.")
        return

    if not json_out:
        typer.echo("Building master style prompt from config/style.yaml ...")
        typer.echo("Calling gpt-image-2 ...")
    result, dest = style_mod.generate_master(lock=lock)
    if json_out:
        typer.echo(json.dumps({
            "action": "lock" if lock else "draft", "quality": "high" if lock else "low",
            "path": str(dest), "bytes": len(result.png_bytes), "usage": result.usage,
        }))
        return
    typer.echo(f"Quality: {'HIGH (locked master)' if lock else 'low (draft)'}")
    typer.echo(f"Saved {len(result.png_bytes):,} bytes -> {dest}")
    if result.usage:
        typer.echo(f"Token usage: {result.usage}")


@app.command()
def gen(
    asset: str = typer.Option("", "--asset", help="Generate just this asset by name."),
    all_: bool = typer.Option(False, "--all", help="Generate every asset in the manifest."),
    quality: str = typer.Option("", "--quality", help="Override quality: low|medium|high."),
    force: bool = typer.Option(False, "--force", help="Ignore the cache and regenerate."),
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON summary."),
) -> None:
    """Generate assets from the manifest via the master reference, using the cache."""
    from .cost import spend_from_usages
    from .generate import generate_all

    if not asset and not all_:
        typer.echo("Specify --asset NAME or --all.")
        raise typer.Exit(code=2)

    outcomes = generate_all(only=asset or None, quality=quality or None, force=force)
    generated = sum(1 for o in outcomes if o.status == "generated")
    cached = sum(1 for o in outcomes if o.status == "cached")
    total = sum(o.tokens or 0 for o in outcomes)
    run = spend_from_usages(o.usage for o in outcomes)

    if json_out:
        typer.echo(json.dumps({
            "outcomes": [{"name": o.name, "status": o.status, "path": str(o.path), "tokens": o.tokens} for o in outcomes],
            "generated": generated, "cached": cached, "tokens": total, "usd": round(run.usd, 6),
        }))
        return

    for o in outcomes:
        tok = f"  ({o.tokens} tokens)" if o.tokens else ""
        typer.echo(f"  [{o.status:9}] {o.name} -> {o.path}{tok}")
    typer.echo(f"Done: {generated} generated, {cached} cached, {total} tokens (~${run.usd:.4f}) this run.")


@app.command()
def process(
    asset: str = typer.Option("", "--asset", help="Process just this asset."),
    enforce_palette: bool = typer.Option(False, "--enforce-palette", help="Snap colors to the locked palette (safety net; off by default)."),
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON summary."),
) -> None:
    """Background-remove, normalize, and write clean metadata-free sprites — no API."""
    from .postprocess import process_assets

    results = process_assets(only=asset or None, enforce=enforce_palette)
    nfiles = sum(len(r["files"]) for r in results if r["status"] == "ok")

    if json_out:
        payload = [
            {"name": r["name"], "status": r["status"],
             **({"class": r["class"], "canvas": r["canvas"], "files": [str(p) for p in r["files"]]}
                if r["status"] == "ok" else {})}
            for r in results
        ]
        typer.echo(json.dumps({"results": payload, "sprites": nfiles}))
        return

    for r in results:
        if r["status"] != "ok":
            typer.echo(f"  [{r['status']}] {r['name']}")
            continue
        sizes = ", ".join(p.name for p in r["files"])
        typer.echo(f"  [ok] {r['name']} ({r['class']}, canvas {r['canvas']}) -> {sizes}")
    typer.echo(f"Done: {nfiles} clean sprites in {config.SPRITES_DIR}, all metadata-verified.")


@app.command()
def pack(
    atlas: bool = typer.Option(False, "--atlas", help="Also pre-pack per-class atlases."),
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON summary."),
) -> None:
    """Emit out/sprites/manifest.json and optionally pack atlases."""
    from .pack import emit_manifest, pack_atlases

    manifest = emit_manifest()
    atlases = [str(a) for a in pack_atlases()] if atlas else []

    if json_out:
        typer.echo(json.dumps({"manifest": str(manifest), "atlases": atlases}))
        return
    typer.echo(f"Manifest -> {manifest}")
    for a in atlases:
        typer.echo(f"Atlas -> {a}")


@app.command()
def handoff(
    path: str = typer.Argument(..., help="Game repo art folder, e.g. ../Assets/Art"),
    atlas: bool = typer.Option(False, "--atlas", help="Include packed atlases in the handoff."),
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON summary."),
) -> None:
    """Copy only clean sprites + manifest into the game repo art folder."""
    from .pack import handoff as do_handoff

    result = do_handoff(path, include_atlas=atlas)
    if json_out:
        typer.echo(json.dumps(result))
        return
    for name in result["copied"]:
        typer.echo(f"  + {name}")
    typer.echo(f"Handed off {len(result['copied'])} files to {result['target']}. Nothing else crossed.")


@app.command()
def build(
    quality: str = typer.Option("", "--quality", help="Override generation quality."),
    enforce_palette: bool = typer.Option(False, "--enforce-palette", help="Snap to the locked palette."),
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON summary."),
) -> None:
    """One shot: generate, background-remove, normalize, clean, and emit the manifest."""
    from .cost import spend_from_usages
    from .generate import generate_all
    from .pack import emit_manifest
    from .postprocess import process_assets

    outcomes = generate_all(quality=quality or None)
    run = spend_from_usages(o.usage for o in outcomes)
    new = sum(1 for o in outcomes if o.status == "generated")
    results = process_assets(enforce=enforce_palette)
    nfiles = sum(len(r["files"]) for r in results if r["status"] == "ok")
    manifest = emit_manifest()

    if json_out:
        typer.echo(json.dumps({
            "generate": {"new": new, "cached": len(outcomes) - new, "usd": round(run.usd, 6)},
            "process": {"sprites": nfiles},
            "manifest": str(manifest),
        }))
        return

    typer.echo(f"1/3 generate: {new} new, {len(outcomes) - new} cached (~${run.usd:.4f} this run)")
    typer.echo(f"2/3 process:  {nfiles} clean, metadata-free sprites")
    typer.echo(f"3/3 manifest: {manifest}")
    typer.echo("Build complete. Run `sprite handoff PATH` to ship finals to the game repo.")


@app.command()
def cost(
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON summary."),
) -> None:
    """Print cumulative token usage and estimated spend from the cache."""
    from .cost import summarize

    s = summarize()
    total = s["total"]

    if json_out:
        def _d(sp):
            return {"text_input": sp.text_input, "image_input": sp.image_input,
                    "image_output": sp.image_output, "calls": sp.calls, "usd": round(sp.usd, 6)}
        typer.echo(json.dumps({
            "records": s["records"],
            "total": _d(total),
            "per_asset": {name: _d(sp) for name, sp in s["per_asset"].items() if sp.calls},
            "rates_per_1m": {
                "text_input": config.PRICE_TEXT_INPUT_PER_M,
                "image_input": config.PRICE_IMAGE_INPUT_PER_M,
                "image_output": config.PRICE_IMAGE_OUTPUT_PER_M,
            },
        }))
        return

    if not total.calls:
        typer.echo("No cached generations yet. Run `sprite gen --all` first.")
        return

    typer.echo(f"Cached generations priced: {total.calls} (sidecars: {s['records']})")
    typer.echo(f"{'asset':22}{'img_out':>9}{'img_in':>8}{'txt_in':>8}{'USD':>10}")
    for name, sp in sorted(s["per_asset"].items()):
        if not sp.calls:
            continue
        typer.echo(f"{name:22}{sp.image_output:>9}{sp.image_input:>8}{sp.text_input:>8}{sp.usd:>10.4f}")
    typer.echo(f"{'TOTAL':22}{total.image_output:>9}{total.image_input:>8}{total.text_input:>8}{total.usd:>10.4f}")
    typer.echo(
        f"\n= ${total.usd:.4f} total. Rates per 1M tokens: text ${config.PRICE_TEXT_INPUT_PER_M:g}, "
        f"image-in ${config.PRICE_IMAGE_INPUT_PER_M:g}, image-out ${config.PRICE_IMAGE_OUTPUT_PER_M:g} "
        "(confirm on the OpenAI pricing page)."
    )


if __name__ == "__main__":
    app()
