#!/usr/bin/env python3
"""Make web photographs for Joyful Creations LI from local originals.

Usage:
    python3 tools/optimize_photos.py
    python3 tools/optimize_photos.py fotos_entrada
    python3 tools/optimize_photos.py fotos_entrada assets/photos

Reads fotos_entrada/{SLOT}-{nn}*.* — for example H1-01.jpg, B1-02-V.tif,
or W2-05-signage.png. Writes assets/photos/{slot}-{nn}-{width}.{avif,webp,jpg}
at 800, 1600, and 2400 pixels wide when the original is at least that wide.
An original narrower than 800 is written at its own width. The tool never
crops, never upscales, and strips EXIF, GPS, and other embedded metadata.

Names for each slot are listed in content/photo_map.csv. This script does
not set permiso, credit, or alt. The site keeps the placeholder until
content/photos.json names a file that exists and has permiso set to true.

Requires Pillow locally (`pip install Pillow`), including AVIF and WebP
save. Pillow is not a dependency of the site. HEIC originals open when
pillow-heif is installed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (800, 1600, 2400)
NAME = re.compile(
    r"^(?P<slot>[A-Za-z]+\d+)-(?P<nn>\d{2})(?P<rest>[A-Za-z0-9-]*)\.(?P<ext>jpe?g|png|tif|tiff|webp|avif|heic)$",
    re.IGNORECASE,
)
OUTPUT_EXT = ("avif", "webp", "jpg")


def clean_image(image: Image.Image) -> Image.Image:
    """Apply orientation, then copy pixels into an image with no metadata."""
    oriented = ImageOps.exif_transpose(image)
    if oriented.mode in ("RGBA", "LA"):
        flat = Image.new("RGB", oriented.size, (255, 255, 255))
        flat.paste(oriented, mask=oriented.getchannel("A"))
        return flat
    if oriented.mode == "RGB":
        pixels = oriented
    else:
        pixels = oriented.convert("RGB")
    fresh = Image.new("RGB", pixels.size)
    fresh.paste(pixels)
    return fresh


def widths_for(source_width: int) -> list[int]:
    chosen = [width for width in TARGETS if width <= source_width]
    if not chosen:
        return [source_width]
    return chosen


def resize_to(image: Image.Image, width: int) -> Image.Image:
    source_w, source_h = image.size
    if width > source_w:
        raise SystemExit(f"Refusing to upscale {source_w}px to {width}px.")
    if width == source_w:
        return image
    height = max(1, round(source_h * width / source_w))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def assert_no_metadata(path: Path) -> None:
    raw = path.read_bytes()
    if b"Exif" in raw or b"GPSInfo" in raw or b"http://ns.adobe.com/" in raw:
        path.unlink(missing_ok=True)
        raise SystemExit(f"Metadata remained in {path.name}.")
    with Image.open(path) as saved:
        exif = saved.getexif()
        if exif and len(exif) > 0:
            path.unlink(missing_ok=True)
            raise SystemExit(f"EXIF remained in {path.name}.")


def save_set(image: Image.Image, dest: Path, stem: str, width: int) -> list[Path]:
    written = []
    base = dest / f"{stem}-{width}"
    jpg = base.with_suffix(".jpg")
    webp = base.with_suffix(".webp")
    avif = base.with_suffix(".avif")
    image.save(jpg, format="JPEG", quality=85, optimize=True, progressive=True)
    image.save(webp, format="WEBP", quality=82, method=6)
    try:
        image.save(avif, format="AVIF", quality=50)
    except (KeyError, OSError, ValueError) as exc:
        jpg.unlink(missing_ok=True)
        webp.unlink(missing_ok=True)
        raise SystemExit(f"Pillow cannot write AVIF ({exc}). Install a Pillow build with AVIF.") from exc
    for path in (avif, webp, jpg):
        assert_no_metadata(path)
        written.append(path)
    return written


def clear_stem(dest: Path, stem: str) -> None:
    for ext in OUTPUT_EXT:
        for path in dest.glob(f"{stem}-*.{ext}"):
            if re.fullmatch(rf"{re.escape(stem)}-\d+\.{ext}", path.name):
                path.unlink()


def collect(source: Path) -> tuple[list[tuple[str, Path]], list[str]]:
    jobs: list[tuple[str, Path]] = []
    skipped: list[str] = []
    seen: dict[str, str] = {}
    for path in sorted(source.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        match = NAME.fullmatch(path.name)
        if not match:
            skipped.append(path.name)
            continue
        stem = f"{match.group('slot')}-{match.group('nn')}{match.group('rest')}".lower()
        if stem in seen:
            raise SystemExit(f"{path.name} and {seen[stem]} both map to {stem}.")
        seen[stem] = path.name
        jobs.append((stem, path))
    return jobs, skipped


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 2:
        print("Usage: python3 tools/optimize_photos.py [fotos_entrada] [assets/photos]", file=sys.stderr)
        return 2
    source = Path(args[0]) if args else ROOT / "fotos_entrada"
    dest = Path(args[1]) if len(args) == 2 else ROOT / "assets" / "photos"
    if not source.is_dir():
        print(f"Input folder not found: {source}", file=sys.stderr)
        print("Put originals in fotos_entrada/{SLOT}-{nn}*.* and run again.", file=sys.stderr)
        return 1
    jobs, skipped = collect(source)
    for name in skipped:
        print(f"skip {name}")
    if not jobs:
        print("No photographs matched {SLOT}-{nn}*.*")
        return 0
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for stem, path in jobs:
        try:
            with Image.open(path) as incoming:
                image = clean_image(incoming)
        except (UnidentifiedImageError, OSError) as exc:
            raise SystemExit(f"Could not open {path.name}: {exc}") from exc
        source_w, source_h = image.size
        if source_w < 1 or source_h < 1:
            raise SystemExit(f"{path.name} has no pixels.")
        clear_stem(dest, stem)
        for width in widths_for(source_w):
            resized = resize_to(image, width)
            if resized.size[0] > source_w or resized.size[1] > source_h:
                raise SystemExit(f"Refusing to enlarge {path.name}.")
            # Proportional resize only: the output ratio stays the source ratio.
            if abs((resized.size[0] / resized.size[1]) - (source_w / source_h)) > 0.02:
                raise SystemExit(f"Resize changed the composition of {path.name}.")
            for written in save_set(resized, dest, stem, width):
                print(written.name)
                count += 1
    print(f"Wrote {count} files from {len(jobs)} photographs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
