#!/usr/bin/env python3
"""Generate Caravela app icons (.png / .ico / .icns) from the brand glyph.

electron-builder reads apps/desktop/assets/icon.{png,ico,icns}. This script
takes the high-res Caravela glyph and produces all three, each with the glyph
centered on a Caravela-navy rounded tile (so the dock/taskbar icon reads as a
real product icon, not a transparent sprite).

Usage:
    python3 make-icons.py <glyph_png> <out_dir>
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

NAVY = (18, 58, 110, 255)  # Caravela Navy #123A6E


def rounded_tile(size: int, glyph: Image.Image, pad_frac: float = 0.16) -> Image.Image:
    """Glyph centered on a navy rounded-rect tile of side `size`."""
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    radius = int(size * 0.22)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    bg = Image.new("RGBA", (size, size), NAVY)
    tile.paste(bg, (0, 0), mask)

    pad = int(size * pad_frac)
    inner = size - 2 * pad
    g = glyph.copy()
    g.thumbnail((inner, inner), Image.LANCZOS)
    gx = (size - g.width) // 2
    gy = (size - g.height) // 2
    tile.paste(g, (gx, gy), g)
    return tile


def main() -> None:
    glyph_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    glyph = Image.open(glyph_path).convert("RGBA")

    # Master 1024 tile
    master = rounded_tile(1024, glyph)

    # icon.png (512, electron-builder's Linux source)
    master.resize((512, 512), Image.LANCZOS).save(out_dir / "icon.png")

    # icon.ico (Windows, multi-res)
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    master.save(out_dir / "icon.ico", sizes=ico_sizes)

    # icon.icns (macOS) — Pillow writes ICNS from a single square image
    try:
        master.save(out_dir / "icon.icns")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] icns generation skipped: {exc}")

    # Runtime window icon: electron/main.cjs (getAppIconPath) hands
    # public/apple-touch-icon.png to BrowserWindow — it's what Windows draws
    # in the taskbar thumbnail header and alt-tab. Upstream ships the Hermes
    # mascot there, so overwrite it with the Caravela tile.
    touch_icon = out_dir.parent / "public" / "apple-touch-icon.png"
    if touch_icon.parent.is_dir():
        master.save(touch_icon)
        print(f"[ok] replaced runtime window icon {touch_icon}")
    elif out_dir.name == "assets":
        print(f"[warn] {touch_icon.parent} not found — window icon NOT replaced")

    print(f"[ok] wrote icon.png / icon.ico / icon.icns to {out_dir}")


if __name__ == "__main__":
    main()
