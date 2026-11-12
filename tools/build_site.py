#!/usr/bin/env python3
"""Generate the Joyful Creations LI static site from /content.

The public HTML is English. Forms are not given an endpoint.
Gold is not applied to text. The logo file is copied as-is and checked by hash.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
EMAIL = "info@joyfulcreationsli.com"
SLOGAN = "Where every celebration tells your story"
BRAND = "Joyful Creations LI"
LEGAL = "Joyful Creations LI LLC"
LOGO_SHA = "981ad0f4a0ba3d7d92fae0eb374efe415a697672afcf65d6b215cdc5ddad69e8"
HANDMADE_LINE = "Handmade, custom favors & stationery · NY · NJ · CT"

STATES = [
    {"@type": "State", "name": "New York"},
    {"@type": "State", "name": "New Jersey"},
    {"@type": "State", "name": "Connecticut"},
]

NAV = [
    (
        "Weddings",
        "weddings",
        [
            ("Overview", "weddings"),
            ("Custom favors", "weddings/custom-favors"),
            ("Day-of details", "weddings/day-of-details"),
        ],
    ),
    (
        "Bar & bat mitzvahs",
        "bar-bat-mitzvahs",
        [
            ("Overview", "bar-bat-mitzvahs"),
            ("Favors", "bar-bat-mitzvahs/favors"),
            ("Day-of details", "bar-bat-mitzvahs/day-of-details"),
        ],
    ),
    (
        "Stationery",
        "stationery",
        [
            ("Overview", "stationery"),
            ("Invitations", "stationery/invitations"),
            ("Portfolio", "stationery/portfolio"),
            ("Inquiry", "stationery/inquiry"),
        ],
    ),
    ("Portfolio", "portfolio", []),
    ("About", "about", []),
]

MORE = [
    ("Other celebrations", "celebrations"),
    ("Bridal showers", "celebrations/bridal-showers"),
    ("Process", "process"),
    ("FAQ", "faq"),
]

PORTFOLIO = [
    ("G1-01", "weddings", "Wedding favors"),
    ("G1-02", "weddings", "Wedding menus"),
    ("G1-03", "weddings", "Wedding escort cards"),
    ("G1-04", "weddings", "Wedding signage"),
    ("G1-05", "mitzvahs", "Bar and bat mitzvah favors"),
    ("G1-06", "mitzvahs", "Bar and bat mitzvah menus"),
    ("G1-07", "mitzvahs", "Bar and bat mitzvah escort cards"),
    ("G1-08", "mitzvahs", "Bar and bat mitzvah seating chart"),
    ("G1-09", "showers", "Bridal shower favors"),
    ("G1-10", "showers", "Bridal shower paper details"),
    ("G1-11", "showers", "Bridal shower favors, second frame"),
    ("G1-12", "showers", "Bridal shower paper details, second frame"),
]

STATIONERY_FRAMES = [
    ("S3-01", "invitations", "Invitation suite"),
    ("S3-02", "invitations", "Invitation suite, second frame"),
    ("S3-03", "menus", "Menus"),
    ("S3-04", "menus", "Menus, second frame"),
    ("S3-05", "cards", "Cards"),
    ("S3-06", "cards", "Cards, second frame"),
    ("S3-07", "signage", "Signage"),
    ("S3-08", "signage", "Signage, second frame"),
]

AREA_NAMES = {
    "service-areas/long-island": "Long Island",
    "service-areas/nyc": "New York City",
    "service-areas/new-jersey": "New Jersey",
    "service-areas/connecticut": "Connecticut",
}


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def depth_of(path: str) -> int:
    return 0 if not path else path.count("/") + 1


def href(depth: int, target: str, mode: str = "relative") -> str:
    if mode == "root":
        return "/" if not target else f"/{target}/"
    if not target:
        return "../" * depth or "./"
    return ("../" * depth) + target + "/"


def asset(depth: int, rel: str, mode: str = "relative") -> str:
    if mode == "root":
        return "/" + rel
    return ("../" * depth) + rel


def words(text: str) -> int:
    return len(text.replace("—", " ").split())


def load_json(name: str):
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


_PHOTOS: dict[str, dict] | None = None

PHOTO_SIZES = {
    "hero": "100vw",
    "wide": "100vw",
    "landscape": "(min-width: 700px) 50vw, 100vw",
    "portrait": "(min-width: 700px) 40vw, 100vw",
    "square": "(min-width: 700px) 33vw, 50vw",
}


def photos() -> dict[str, dict]:
    global _PHOTOS
    if _PHOTOS is None:
        raw = load_json("photos.json")
        if not isinstance(raw, list):
            raise SystemExit("content/photos.json must be a list of photo slots.")
        loaded: dict[str, dict] = {}
        for item in raw:
            photo_id = item.get("id")
            if not isinstance(photo_id, str) or not photo_id or photo_id in loaded:
                raise SystemExit(f"photos.json has a missing or duplicate id: {photo_id!r}")
            loaded[photo_id] = item
        _PHOTOS = loaded
    return _PHOTOS


def jpeg_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        raise SystemExit(f"Not a JPEG: {path}")
    index = 2
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while index + 1 < len(data):
        if data[index] != 0xFF:
            break
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            break
        marker = data[index]
        index += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        if index + 2 > len(data):
            break
        length = int.from_bytes(data[index : index + 2], "big")
        if marker in sof and index + 7 <= len(data):
            height = int.from_bytes(data[index + 3 : index + 5], "big")
            width = int.from_bytes(data[index + 5 : index + 7], "big")
            return width, height
        if length < 2:
            break
        index += length
    raise SystemExit(f"JPEG size not found: {path}")


def photo_files(stem: str) -> dict[str, list[tuple[int, Path]]]:
    folder = ROOT / "assets" / "photos"
    found: dict[str, list[tuple[int, Path]]] = {"avif": [], "webp": [], "jpg": []}
    if not folder.is_dir():
        return found
    for ext in ("avif", "webp", "jpg", "jpeg"):
        key = "jpg" if ext == "jpeg" else ext
        for path in sorted(folder.glob(f"{stem}-*.{ext}")):
            match = re.fullmatch(rf"{re.escape(stem)}-(\d+)\.{ext}", path.name)
            if match:
                found[key].append((int(match.group(1)), path))
    for items in found.values():
        items.sort()
    return found


def photo_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def placeholder(slot: str, variant: str, description: str, caption: str) -> str:
    return f"""
<figure class="ph ph-{esc(variant)}">
  <div class="ph-frame">
    <span class="ph-rule" aria-hidden="true"></span>
    <p class="ph-kicker">[PENDIENTE]</p>
    <p class="ph-id">{esc(slot)}</p>
    <p class="ph-desc">{esc(description)}</p>
  </div>
  <figcaption>{esc(caption)}</figcaption>
</figure>
""".strip()


def picture_for(entry: dict, variant: str, depth: int, mode: str) -> str | None:
    """Responsive picture, or None when the slot is not cleared to publish."""
    if entry.get("permiso") is not True:
        return None
    stem = photo_text(entry.get("file")).lower()
    if not stem or "/" in stem or "\\" in stem or ".." in stem:
        return None
    groups = photo_files(stem)
    jpegs = groups["jpg"]
    if not jpegs:
        return None
    width, height = jpeg_size(jpegs[-1][1])
    declared_w = entry.get("width")
    declared_h = entry.get("height")
    if isinstance(declared_w, int) and isinstance(declared_h, int) and declared_w > 0 and declared_h > 0:
        width, height = declared_w, declared_h
    sizes = PHOTO_SIZES.get(variant, "100vw")
    loading = "eager" if variant == "hero" else "lazy"

    def srcset(items: list[tuple[int, Path]]) -> str:
        parts = []
        for item_width, path in items:
            url = asset(depth, f"assets/photos/{path.name}", mode)
            parts.append(f"{esc(url)} {item_width}w")
        return ", ".join(parts)

    lines = ["<picture>"]
    for ext, mime in (("avif", "image/avif"), ("webp", "image/webp")):
        if groups[ext]:
            lines.append(f'  <source type="{mime}" srcset="{srcset(groups[ext])}" sizes="{esc(sizes)}">')
    src = asset(depth, f"assets/photos/{jpegs[-1][1].name}", mode)
    lines.append(
        "  "
        + f'<img src="{esc(src)}" srcset="{srcset(jpegs)}" sizes="{esc(sizes)}" '
        + f'width="{width}" height="{height}" alt="{esc(photo_text(entry.get("alt")))}" loading="{loading}">'
    )
    lines.append("</picture>")
    picture = "\n".join("    " + line for line in lines)
    alt = photo_text(entry.get("alt"))
    credit = photo_text(entry.get("credito")) or photo_text(entry.get("credit"))
    bits = []
    if alt:
        bits.append(esc(alt))
    if credit:
        bits.append(f'<span class="credit">Photo: {esc(credit)}</span>')
    caption_html = ""
    if bits:
        caption_html = "\n  <figcaption>\n    " + "\n    ".join(bits) + "\n  </figcaption>"
    return f"""<figure class="ph ph-{esc(variant)} ph-has-photo">
  <div class="ph-frame">
{picture}
  </div>{caption_html}
</figure>"""


def ph(
    slot: str,
    variant: str,
    description: str,
    caption: str,
    *,
    photo: str | None = None,
    depth: int = 0,
    mode: str = "relative",
) -> str:
    """Placeholder frame, or a picture when the slot file exists and permiso is true."""
    if not photo:
        return placeholder(slot, variant, description, caption)
    entry = photos().get(photo)
    if entry is None:
        raise SystemExit(f"photos.json has no entry for {photo}")
    rendered = picture_for(entry, variant, depth, mode)
    if rendered is None:
        return placeholder(slot, variant, description, caption)
    return rendered


def piece_caption(piece: str) -> str:
    return (
        f"Placeholder for {piece} by Joyful Creations LI. "
        "This is not a photograph. This is not an event by Joyful Creations LI. "
        "No client or venue is named."
    )


def faq_html(faq: dict, ids: list[str]) -> str:
    by_id = {item["id"]: item for item in faq["items"]}
    rows = []
    for fid in ids:
        item = by_id[fid]
        rows.append(f"<div><dt>{esc(item['q'])}</dt><dd>{esc(item['a'])}</dd></div>")
    return '<dl class="faq-list">' + "".join(rows) + "</dl>"


def faq_schema(faq: dict, ids: list[str]) -> dict:
    by_id = {item["id"]: item for item in faq["items"]}
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": by_id[fid]["q"],
                "acceptedAnswer": {"@type": "Answer", "text": by_id[fid]["a"]},
            }
            for fid in ids
        ],
    }


def crumbs_html(depth: int, crumbs: list[tuple[str, str | None]], mode: str) -> str:
    if not crumbs:
        return ""
    items = []
    for label, target in crumbs:
        if target is None:
            items.append(f"<li aria-current=\"page\">{esc(label)}</li>")
        else:
            items.append(f'<li><a href="{href(depth, target, mode)}">{esc(label)}</a></li>')
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{"".join(items)}</ol></nav>'


def cta(depth: int, mode: str, heading: str | None = None, target: str = "quote", label: str = "Request a consultation") -> str:
    title = f"<h2>{esc(heading)}</h2>" if heading else ""
    return f"""
<section class="section band">
  <div class="wrap">
    {title}
    <a class="btn btn-primary" href="{href(depth, target, mode)}">{esc(label)}</a>
  </div>
</section>
""".strip()


def faq_section(depth: int, faq: dict, ids: list[str], mode: str) -> str:
    return f"""
<section class="section">
  <div class="wrap">
    <h2>Questions</h2>
    {faq_html(faq, ids)}
    <p><a href="{href(depth, "faq", mode)}">Read the FAQ</a></p>
  </div>
</section>
""".strip()


def current(page_path: str, target: str) -> str:
    return ' aria-current="page"' if page_path == target else ""


def nav_desktop(depth: int, page_path: str, mode: str) -> str:
    items = []
    for label, target, children in NAV:
        child_html = ""
        if children:
            links = "".join(
                f'<li><a href="{href(depth, child_target, mode)}"{current(page_path, child_target)}>{esc(child_label)}</a></li>'
                for child_label, child_target in children
            )
            child_html = f'<ul class="menu-sub">{links}</ul>'
        items.append(
            f'<li class="has-sub"><a href="{href(depth, target, mode)}"{current(page_path, target)}>{esc(label)}</a>{child_html}</li>'
        )
    more_links = "".join(
        f'<li><a href="{href(depth, target, mode)}"{current(page_path, target)}>{esc(label)}</a></li>'
        for label, target in MORE
    )
    items.append(
        '<li class="has-sub"><button type="button" class="nav-more" aria-expanded="false" aria-haspopup="true">More</button>'
        f'<ul class="menu-sub">{more_links}</ul></li>'
    )
    return f'<nav class="primary-nav" aria-label="Primary"><ul>{"".join(items)}</ul></nav>'


def nav_mobile(depth: int, page_path: str, mode: str) -> str:
    blocks = [
        f'<button type="button" class="btn btn-secondary" data-close-menu>Close</button>',
        f'<p class="nav-label">Menu</p>',
        f'<p><a href="{href(depth, "quote", mode)}">Request a consultation</a></p>',
    ]
    for label, target, children in NAV:
        blocks.append(f'<p class="nav-label">{esc(label)}</p><ul>')
        blocks.append(f'<li><a href="{href(depth, target, mode)}"{current(page_path, target)}>{esc(label)}</a></li>')
        for child_label, child_target in children:
            if child_target == target:
                continue
            blocks.append(
                f'<li><a href="{href(depth, child_target, mode)}"{current(page_path, child_target)}>{esc(child_label)}</a></li>'
            )
        blocks.append("</ul>")
    blocks.append('<p class="nav-label">More</p><ul>')
    for label, target in MORE:
        blocks.append(f'<li><a href="{href(depth, target, mode)}"{current(page_path, target)}>{esc(label)}</a></li>')
    blocks.append("</ul>")
    inner = "".join(blocks)
    return f'<div id="mobile-nav" class="nav-panel" hidden>{inner}</div>'


def footer(depth: int, mode: str, listings: dict) -> str:
    live = [
        item
        for item in listings["listings"]
        if item.get("estado") == "publicado" and item.get("url")
    ]
    find_us = ""
    if live:
        links = "".join(
            f'<li><a href="{esc(item["url"])}">{esc(item["nombre"])}</a></li>'
            for item in live
        )
        find_us = f'<div><h2>Find us on</h2><ul>{links}</ul></div>'
    services = [
        ("Weddings", "weddings"),
        ("Bar & bat mitzvahs", "bar-bat-mitzvahs"),
        ("Stationery", "stationery"),
        ("Invitations", "stationery/invitations"),
        ("Bridal showers", "celebrations/bridal-showers"),
    ]
    studio = [("About", "about"), ("Process", "process"), ("FAQ", "faq"), ("Contact", "contact")]
    areas = [
        ("Service areas", "service-areas"),
        ("Long Island", "service-areas/long-island"),
        ("New York City", "service-areas/nyc"),
        ("New Jersey", "service-areas/new-jersey"),
        ("Connecticut", "service-areas/connecticut"),
    ]

    def column(title: str, links: list[tuple[str, str]]) -> str:
        items = "".join(
            f'<li><a href="{href(depth, target, mode)}">{esc(label)}</a></li>' for label, target in links
        )
        return f"<div><h2>{esc(title)}</h2><ul>{items}</ul></div>"

    logo = asset(depth, "marca/logo-joyful-creations.png", mode)
    return f"""
<footer class="site-footer">
  <div class="wrap">
    <a class="logo-lockup" href="{href(depth, "", mode)}">
      <img src="{logo}" width="1920" height="1280" alt="Joyful Creations logo">
    </a>
    <p class="footer-slogan">{esc(SLOGAN)}</p>
    <p>{esc(HANDMADE_LINE)}</p>
    <div class="footer-grid">
      {column("Services", services)}
      {column("Studio", studio)}
      {column("Areas", areas)}
      {find_us}
    </div>
    <p><a href="mailto:{EMAIL}">{EMAIL}</a></p>
    <p class="legal-line"><a href="{href(depth, "privacy", mode)}">Privacy</a> · © {esc(LEGAL)}</p>
  </div>
</footer>
""".strip()


def shell(page: dict, main: str, schemas: list, listings: dict, mode: str = "relative") -> str:
    path = page["path"]
    if path == "404":
        depth = 0
        canonical = "/404.html"
    else:
        depth = depth_of(path)
        canonical = href(depth, path, mode)
    title = page["title"]
    description = page["description"]
    if len(description) > 155:
        raise SystemExit(f"Description too long ({len(description)}): {path}")
    if BRAND not in title:
        raise SystemExit(f"Title missing brand: {path}")
    css = asset(depth, "assets/css/site.css", mode)
    js = asset(depth, "assets/js/site.js", mode)
    og = asset(depth, "marca/icons/og-image-1200x630.png", mode)
    manifest = asset(depth, "manifest.webmanifest", mode)
    favicon_ico = asset(depth, "marca/icons/favicon.ico", mode)
    favicon_16 = asset(depth, "marca/icons/favicon-16.png", mode)
    favicon_32 = asset(depth, "marca/icons/favicon-32.png", mode)
    apple = asset(depth, "marca/icons/apple-touch-icon-180.png", mode)
    font_display = asset(depth, "assets/fonts/cormorant-garamond-500-italic.woff2", mode)
    font_body = asset(depth, "assets/fonts/jost-400.woff2", mode)
    robots = '<meta name="robots" content="noindex">' if page.get("noindex") else ""
    schema = json.dumps({"@context": "https://schema.org", "@graph": schemas}, ensure_ascii=False)
    schema = schema.replace("<", "\\u003c")
    data_page = path or "home"
    prefix_script = ""
    if mode == "root":
        prefix_script = """
<script>
(function () {
  var marker = "/joyful-creations/";
  var at = location.pathname.indexOf(marker);
  if (at === -1) return;
  var root = location.pathname.slice(0, at) + marker;
  document.querySelectorAll("[data-root]").forEach(function (el) {
    el.setAttribute("href", root + el.getAttribute("data-root"));
  });
})();
</script>
""".strip()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{esc(canonical)}">
  {robots}
  <meta name="theme-color" content="#FBF7F1">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:image" content="{esc(og)}">
  <meta property="og:image:alt" content="Joyful Creations logo on an ivory background">
  <meta property="og:locale" content="en_US">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">
  <meta name="twitter:image" content="{esc(og)}">
  <meta name="twitter:image:alt" content="Joyful Creations logo on an ivory background">
  <link rel="icon" href="{favicon_ico}" sizes="any">
  <link rel="icon" type="image/png" sizes="32x32" href="{favicon_32}">
  <link rel="icon" type="image/png" sizes="16x16" href="{favicon_16}">
  <link rel="apple-touch-icon" href="{apple}">
  <link rel="manifest" href="{manifest}">
  <link rel="preload" href="{font_display}" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="{font_body}" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="{css}">
  <!-- META_PIXEL_SLOT -->
  <!-- X_PIXEL_SLOT -->
  <script type="application/ld+json">{schema}</script>
</head>
<body data-page="{esc(data_page)}">
  <a class="skip" href="#content">Skip to content</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="brand brand-full" href="{href(depth, "", mode)}">
        <img src="{asset(depth, "marca/logo-joyful-creations.png", mode)}" width="1920" height="1280" alt="Joyful Creations logo, home">
      </a>
      <a class="brand brand-mono" href="{href(depth, "", mode)}">
        <img src="{asset(depth, "marca/icons/monogram-jc-source-crop.png", mode)}" width="465" height="391" alt="Joyful Creations JC monogram, home">
      </a>
      {nav_desktop(depth, path, mode)}
      <a class="btn btn-primary header-cta" href="{href(depth, "quote", mode)}">Request a consultation</a>
      <button type="button" class="menu-toggle" aria-expanded="false" aria-controls="mobile-nav" aria-label="Open menu">
        <span class="bar"></span><span class="bar"></span><span class="bar"></span>
      </button>
    </div>
  </header>
  {nav_mobile(depth, path, mode)}
  <main id="content" tabindex="-1">
    {main}
  </main>
  {footer(depth, mode, listings)}
  <a class="btn btn-primary mobile-bar" href="{href(depth, "quote", mode)}">Request a consultation</a>
  {prefix_script}
  <script src="{js}" defer></script>
</body>
</html>
"""


def provider() -> dict:
    return {
        "@type": "LocalBusiness",
        "name": BRAND,
        "email": EMAIL,
        "areaServed": STATES,
    }


def crumb_schema(crumbs: list[tuple[str, str | None]]) -> dict:
    items = []
    for index, (label, target) in enumerate(crumbs, start=1):
        entry = {"@type": "ListItem", "position": index, "name": label}
        if target is not None:
            entry["item"] = "/" if not target else f"/{target}/"
        items.append(entry)
    return {"@type": "BreadcrumbList", "itemListElement": items}


def base_schema(page: dict) -> list:
    path = page["path"]
    node = {
        "@type": "WebPage",
        "name": page["title"],
        "description": page["description"],
        "inLanguage": "en",
        "isPartOf": {"@type": "WebSite", "name": BRAND, "inLanguage": "en"},
    }
    if path == "":
        node["@type"] = "WebPage"
    return [node]


def home_schema() -> list:
    logo = "/marca/logo-joyful-creations.png"
    business = {
        "@type": "LocalBusiness",
        "@id": "#business",
        "name": BRAND,
        "slogan": SLOGAN,
        "email": EMAIL,
        "image": logo,
        "areaServed": STATES,
        "founder": {"@type": "Person", "name": "Jonah"},
    }
    website = {
        "@type": "WebSite",
        "name": BRAND,
        "slogan": SLOGAN,
        "inLanguage": "en",
    }
    organization = {
        "@type": "Organization",
        "name": BRAND,
        "legalName": LEGAL,
        "slogan": SLOGAN,
        "email": EMAIL,
        "logo": logo,
    }
    return [business, website, organization]


def service_schema(page: dict, area_name: str | None = None) -> dict:
    area = STATES
    if area_name:
        kind = "State" if area_name in {"New Jersey", "Connecticut"} else "AdministrativeArea"
        area = [{"@type": kind, "name": area_name}]
    return {
        "@type": "Service",
        "name": page["h1"],
        "description": page["description"],
        "provider": provider(),
        "areaServed": area,
        "serviceType": "Handmade favors and stationery",
    }


def image_schemas(frames: list[tuple[str, str, str]]) -> list:
    nodes = []
    for slot, _cat, piece in frames:
        nodes.append(
            {
                "@type": "ImageObject",
                "name": f"Placeholder {slot}",
                "caption": piece_caption(piece),
                "creditText": "No photographer is credited because no event photograph is published.",
            }
        )
    return nodes


def text_field(fid, name, label, required, input_type="text", autocomplete="", extra=""):
    star = " *" if required else " (optional)"
    req_attr = " required" if required else ""
    data = ' data-required="text"' if required else ""
    ac = f' autocomplete="{esc(autocomplete)}"' if autocomplete else ""
    return f"""
<div class="form-row">
  <label for="{fid}">{esc(label + star)}</label>
  <input id="{fid}" name="{name}" type="{input_type}"{req_attr}{data} data-label="{esc(label.lower())}" aria-describedby="{fid}-error"{ac} {extra}>
  <p class="form-error" id="{fid}-error"></p>
</div>
""".strip()


def select_field(fid, name, label, options, required):
    star = " *" if required else " (optional)"
    req_attr = " required" if required else ""
    data = ' data-required="select"' if required else ""
    choices = ['<option value="">Select an option</option>']
    for value, text in options:
        choices.append(f'<option value="{esc(value)}">{esc(text)}</option>')
    return f"""
<div class="form-row">
  <label for="{fid}">{esc(label + star)}</label>
  <select id="{fid}" name="{name}"{req_attr}{data} aria-describedby="{fid}-error">{"".join(choices)}</select>
  <p class="form-error" id="{fid}-error"></p>
</div>
""".strip()


def check_group(fid, legend, name, options, required=True):
    boxes = []
    for index, (value, label) in enumerate(options):
        boxes.append(
            f'<div class="check"><input type="checkbox" id="{fid}-{index}" name="{name}" value="{esc(value)}"><label for="{fid}-{index}">{esc(label)}</label></div>'
        )
    req = ' data-required="group"' if required else ""
    star = " *" if required else " (optional)"
    return f"""
<fieldset class="checks"{req} data-label="{esc(legend)}">
  <legend class="field-legend" id="{fid}">{esc(legend + star)}</legend>
  {"".join(boxes)}
  <p class="form-error" id="{fid}-error"></p>
</fieldset>
""".strip()


def hidden_utm() -> str:
    names = ["utm_source", "utm_medium", "utm_campaign", "utm_content"]
    return "".join(f'<input type="hidden" name="{name}" value="">' for name in names)


def review_note() -> str:
    return """
<div class="review-note">
  <p class="kicker">Review build</p>
  <p>This form does not send. Nothing is emailed, and no form service is used. The intended mailbox, when a send is connected later, is info@joyfulcreationsli.com. No payment is taken here.</p>
</div>
""".strip()


def quote_form(depth: int, mode: str) -> str:
    looking = [
        ("favors", "Favors"),
        ("menus", "Menus"),
        ("escort-cards", "Escort cards"),
        ("table-numbers", "Table numbers"),
        ("seating-chart", "Seating chart"),
        ("day-of-signage", "Day-of signage"),
        ("invitations", "Invitations"),
        ("other", "Other"),
    ]
    heard = [
        ("google", "Google"),
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("x", "X"),
        ("the-knot", "The Knot"),
        ("zola", "Zola"),
        ("referral", "Planner or vendor referral"),
        ("friend", "Friend"),
        ("other", "Other"),
    ]
    events = [
        ("bar-bat-mitzvah", "Bar/Bat Mitzvah"),
        ("wedding", "Wedding"),
        ("bridal-shower", "Bridal shower"),
        ("other", "Other celebration"),
    ]
    return f"""
<form id="quote-form" data-review-form data-thank-you="{href(depth, "thank-you", mode)}" method="post" action="" onsubmit="event.preventDefault();" novalidate>
  {review_note()}
  <div id="form-status" role="alert" aria-live="assertive"></div>
  <div class="hp" aria-hidden="true">
    <label for="company-website">Company website</label>
    <input id="company-website" name="company_website" type="text" tabindex="-1" autocomplete="off">
  </div>
  {text_field("full-name", "full_name", "Full name", True, "text", "name")}
  {text_field("email", "email", "Email", True, "email", "email")}
  {text_field("phone", "phone", "Phone", False, "tel", "tel")}
  {select_field("event-type", "event_type", "Event type", events, True)}
  {text_field("event-date", "event_date", "Event date", True, "date")}
  {text_field("location", "location", "Event location (city/state)", True, "text")}
  {text_field("guest-count", "guest_count", "Approximate guest count", False, "number", extra='min="1" inputmode="numeric"')}
  {check_group("looking-for", "What are you looking for?", "looking_for", looking, True)}
  <div class="form-row">
    <label for="celebration-notes">Tell us about your celebration (optional)</label>
    <textarea id="celebration-notes" name="notes" aria-describedby="celebration-notes-error"></textarea>
    <p class="form-error" id="celebration-notes-error"></p>
  </div>
  {select_field("heard", "heard", "How did you hear about us?", heard, False)}
  <div class="form-row">
    <div class="check">
      <input type="checkbox" id="consent" name="consent" value="yes" required aria-describedby="consent-error">
      <label for="consent">I agree to be contacted by email about my request. *</label>
    </div>
    <p class="form-error" id="consent-error"></p>
  </div>
  <p>Read the <a href="{href(depth, "privacy", mode)}">privacy page</a> before you agree. It explains what these fields are for.</p>
  {hidden_utm()}
  <button class="btn btn-primary" type="submit">Review request</button>
  <noscript><p>This form does not send. Email {EMAIL}.</p></noscript>
</form>
""".strip()


def inquiry_form(depth: int, mode: str) -> str:
    pieces = [
        ("invitation-suite", "Invitation suite"),
        ("save-the-dates", "Save the dates"),
        ("menus", "Menus"),
        ("escort-cards", "Escort/place cards"),
        ("table-numbers", "Table numbers"),
        ("seating-chart", "Seating chart"),
        ("signage", "Signage"),
        ("other", "Other"),
    ]
    finish = [("flat-print", "Flat print"), ("not-sure", "Not sure")]
    return f"""
<form id="inquiry-form" data-review-form data-thank-you="{href(depth, "thank-you", mode)}" method="post" action="" enctype="multipart/form-data" onsubmit="event.preventDefault();" novalidate>
  {review_note()}
  <div id="form-status" role="alert" aria-live="assertive"></div>
  <div class="hp" aria-hidden="true">
    <label for="company-website-inquiry">Company website</label>
    <input id="company-website-inquiry" name="company_website" type="text" tabindex="-1" autocomplete="off">
  </div>
  {text_field("inquiry-name", "full_name", "Full name", True, "text", "name")}
  {text_field("inquiry-email", "email", "Email", True, "email", "email")}
  {check_group("piece-type", "Piece type", "piece_type", pieces, True)}
  {text_field("quantity", "quantity", "Quantity (approx.)", True, "number", extra='min="1" inputmode="numeric"')}
  {text_field("needed-by", "needed_by", "Needed by", True, "date")}
  {select_field("finish", "finish", "Finish", finish, False)}
  <div class="form-row">
    <label for="inspiration">Inspiration images (optional)</label>
    <input id="inspiration" name="inspiration" type="file" accept="image/*" multiple aria-describedby="inspiration-error inspiration-hint">
    <p id="inspiration-hint" class="credit">Up to 3 images. Each file must be 10 MB or smaller. Files stay in this browser and are not uploaded.</p>
    <p class="form-error" id="inspiration-error"></p>
  </div>
  <div class="form-row">
    <label for="inquiry-notes">Notes (optional)</label>
    <textarea id="inquiry-notes" name="notes" aria-describedby="inquiry-notes-error"></textarea>
    <p class="form-error" id="inquiry-notes-error"></p>
  </div>
  <div class="form-row">
    <div class="check">
      <input type="checkbox" id="inquiry-consent" name="consent" value="yes" required aria-describedby="inquiry-consent-error">
      <label for="inquiry-consent">I agree to be contacted by email about my request. *</label>
    </div>
    <p class="form-error" id="inquiry-consent-error"></p>
  </div>
  <p>Read the <a href="{href(depth, "privacy", mode)}">privacy page</a> before you agree.</p>
  {hidden_utm()}
  <button class="btn btn-primary" type="submit">Review request</button>
  <noscript><p>This form does not send. Email {EMAIL}.</p></noscript>
</form>
""".strip()


def filter_gallery(frames, filters, depth: int, mode: str) -> str:
    buttons = ['<button type="button" data-filter="all" aria-pressed="true">All</button>']
    for key, label in filters:
        buttons.append(
            f'<button type="button" data-filter="{esc(key)}" aria-pressed="false">{esc(label)}</button>'
        )
    cards = []
    for slot, cat, piece in frames:
        cards.append(
            f'<div class="span-4 gallery-item" data-cat="{esc(cat)}">{ph(slot, "square", "Real photograph not provided. Intended subject: " + piece + ".", piece_caption(piece), photo=slot, depth=depth, mode=mode)}</div>'
        )
    return f"""
<div data-filter-group>
  <div class="filters" role="group" aria-label="Filter portfolio">{"".join(buttons)}</div>
  <p data-filter-empty hidden>No frames in this group.</p>
  <div class="grid gallery">{"".join(cards)}</div>
</div>
""".strip()


def steps(items: list[tuple[str, str]], five: bool = False) -> str:
    lis = []
    for index, (title, text) in enumerate(items, start=1):
        lis.append(f"<li><span class=\"step-no\">{index}</span><h3>{esc(title)}</h3><p>{esc(text)}</p></li>")
    klass = "steps steps-5" if five else "steps"
    return f'<ol class="{klass}">{"".join(lis)}</ol>'


def render_home(page, faq, mode):
    depth = depth_of(page["path"])
    featured = [item for item in PORTFOLIO if item[0] in {"G1-01", "G1-02", "G1-03", "G1-05", "G1-06", "G1-07"}]
    cards = "".join(
        f'<div class="span-4 gallery-item">{ph(slot, "square", "Real photograph not provided. Intended subject: " + piece + ".", piece_caption(piece), photo=slot, depth=depth, mode=mode)}</div>'
        for slot, _cat, piece in featured
    )
    return f"""
<section class="hero">
  {ph("H1", "hero", "Intended subject: a wedding reception table with a menu, a table number, and a favor. Real photograph not provided.", "Placeholder H1. Not a photograph of finished work, and not an event by Joyful Creations LI.", photo="H1-01", depth=depth, mode=mode)}
  <div class="wrap hero-copy">
    <p class="tagline">{esc(SLOGAN)}</p>
    <h1>{esc(page["h1"])}</h1>
    <p class="sub">Custom pieces designed and made by hand for your wedding or mitzvah — and for every celebration in between — across New York, New Jersey and Connecticut.</p>
    <div class="actions">
      <a class="btn btn-primary" href="{href(depth, "quote", mode)}">Request a consultation</a>
      <a class="btn btn-secondary" href="{href(depth, "portfolio", mode)}">View the portfolio</a>
    </div>
  </div>
</section>
<section class="section">
  <div class="wrap grid">
    <div class="span-4">
      <a class="card-link" href="{href(depth, "weddings", mode)}">
        {ph("W2", "landscape", "Intended subject: wedding day-of paper. Real photograph not provided.", "Placeholder W2. Not a photograph of finished work.", photo="W2-01-menus", depth=depth, mode=mode)}
        <h2>Weddings</h2>
      </a>
    </div>
    <div class="span-4">
      <a class="card-link" href="{href(depth, "bar-bat-mitzvahs", mode)}">
        {ph("M1", "landscape", "Intended subject: a bar or bat mitzvah table or display. Real photograph not provided.", "Placeholder M1. Not a photograph of finished work.", photo="M1-01", depth=depth, mode=mode)}
        <h2>Bar &amp; bat mitzvahs</h2>
      </a>
    </div>
    <div class="span-4">
      <a class="card-link" href="{href(depth, "stationery", mode)}">
        {ph("S1", "landscape", "Intended subject: an invitation suite, flat lay. Real photograph not provided.", "Placeholder S1. Not a photograph of finished work.", photo="S1-01", depth=depth, mode=mode)}
        <h2>Stationery</h2>
      </a>
    </div>
  </div>
</section>
<section class="section band">
  <div class="wrap grid">
    <div class="span-6">
      {ph("H2", "landscape", "Intended subject: an escort-card display, to sit beside the wedding hero. Real photograph not provided.", "Placeholder H2. Not a photograph of finished work.", photo="H2-01", depth=depth, mode=mode)}
    </div>
    <div class="span-6">
      <h2>Every piece is custom. Every detail is handmade.</h2>
      <h3>Made by hand</h3>
      <p>Favors, menus, escort cards, seating charts, and signage are planned for one celebration and finished by hand.</p>
      {ph("H3", "wide", "Intended subject: a paper detail. Real photograph not provided.", "Placeholder H3. Not a photograph of finished work.", photo="H3-01", depth=depth, mode=mode)}
    </div>
  </div>
</section>
<section class="section">
  <div class="wrap grid">
    <div class="span-6 bio-copy">
      <h2>Meet Jonah</h2>
      <p>Meet Jonah — in the craft since 2010.</p>
      <div class="pending"><p>[PENDIENTE] A longer note about earlier events work is not confirmed on this page.</p></div>
      <a class="btn btn-secondary" href="{href(depth, "about", mode)}">Meet Jonah</a>
    </div>
    <div class="span-6 bio-photo">
      {ph("B1", "landscape", "Intended subject: a horizontal portrait of Jonah. Real photograph not provided. No face is shown.", "Placeholder B1, horizontal. Not a photograph.", photo="B1-01-H", depth=depth, mode=mode)}
    </div>
  </div>
</section>
<section class="section band">
  <div class="wrap">
    <h2>Selected work</h2>
    <p>Six labeled frames stand in for photographs that are not published yet. Three are for weddings and three are for bar and bat mitzvahs.</p>
    <div class="grid gallery">{cards}</div>
    <p><a class="btn btn-secondary" href="{href(depth, "portfolio", mode)}">See more work</a></p>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <h2>How an order moves</h2>
    {steps([
        ("Consultation", "We start with a conversation about the celebration and the pieces you need."),
        ("Design", "Pieces are designed for that celebration."),
        ("Handmade", "The pieces the studio takes on are made by hand."),
    ])}
    <div class="pending"><p>Delivery, pickup, and on-site setup are not confirmed on this site.</p></div>
    <p><a href="{href(depth, "process", mode)}">Read the process</a></p>
  </div>
</section>
<section class="section band">
  <div class="wrap grid">
    <div class="span-6">
      <p class="kicker">Also</p>
      <h2>Bridal showers and other celebrations</h2>
      <p>These sit beside weddings and bar and bat mitzvahs. They are not the center of the studio.</p>
      <a class="btn btn-secondary" href="{href(depth, "celebrations", mode)}">Other celebrations</a>
    </div>
    <div class="span-6">
      {ph("R1", "landscape", "Intended subject: a bridal shower table with favors and paper. Real photograph not provided.", "Placeholder R1. Not a photograph of finished work.", photo="R1-01", depth=depth, mode=mode)}
    </div>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <h2>Where we serve</h2>
    <p>Long Island · New York City · New Jersey · Connecticut</p>
    <ul class="area-list">
      <li><a href="{href(depth, "service-areas/long-island", mode)}">Long Island</a></li>
      <li><a href="{href(depth, "service-areas/nyc", mode)}">New York City</a></li>
      <li><a href="{href(depth, "service-areas/new-jersey", mode)}">New Jersey</a></li>
      <li><a href="{href(depth, "service-areas/connecticut", mode)}">Connecticut</a></li>
    </ul>
  </div>
</section>
{cta(depth, mode, "Planning a celebration? Let's design it together.")}
"""


def render_about(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("About", None)]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <div class="grid">
      <div class="span-5">
        {ph("B1", "portrait", "Intended subject: a vertical portrait of Jonah. Real photograph not provided. No face is shown.", "Placeholder B1, vertical. Not a photograph. A last name is not published.", photo="B1-02-V", depth=depth, mode=mode)}
      </div>
      <div class="span-7">
        <h1>{esc(page["h1"])}</h1>
        <p>I've been creating handmade pieces since 2010.</p>
        <div class="pending"><p>[PENDIENTE] Earlier events work, the place it happened, and events from those years are not published here. Other people's events are not claimed as this studio's productions.</p></div>
        <p>Joyful Creations LI was founded in 2023.</p>
      </div>
    </div>
  </div>
</section>
<section class="section band">
  <div class="wrap">
    <h2>How Jonah works</h2>
    <p>Everything is custom. I design every piece myself and make it by hand.</p>
    <div class="grid">
      <div class="span-6">{ph("B2", "landscape", "Intended subject: hands working on a piece. Real photograph not provided.", "Placeholder B2, first frame. Not a photograph.", photo="B2-01", depth=depth, mode=mode)}</div>
      <div class="span-6">{ph("B2", "landscape", "Intended subject: a piece in process. Real photograph not provided.", "Placeholder B2, second frame. Not a photograph.", photo="B2-02", depth=depth, mode=mode)}</div>
    </div>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <h2>Where the studio serves</h2>
    <p>Joyful Creations LI serves celebrations in New York, New Jersey, and Connecticut.</p>
    <a class="btn btn-primary" href="{href(depth, "quote", mode)}">Request a consultation</a>
  </div>
</section>
"""


def render_weddings(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Weddings", None)]
    ids = ["lead-time", "custom", "seating"]
    return f"""
<section class="hero">
  {ph("W2", "hero", "Intended subject: wedding day-of paper. Real photograph not provided.", "Placeholder W2. Not a photograph of finished work.", photo="W2-01-menus", depth=depth, mode=mode)}
  <div class="wrap hero-copy">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="sub">From welcome to farewell, the paper details and favors your guests will remember — designed around your celebration.</p>
  </div>
</section>
<section class="section">
  <div class="wrap grid">
    <div class="span-6">
      <a class="card-link" href="{href(depth, "weddings/custom-favors", mode)}">
        {ph("W1", "landscape", "Intended subject: wedding favors. Real photograph not provided.", "Placeholder W1. Not a photograph of finished work.", photo="W1-01", depth=depth, mode=mode)}
        <h2>Custom favors</h2>
      </a>
    </div>
    <div class="span-6">
      <a class="card-link" href="{href(depth, "weddings/day-of-details", mode)}">
        {ph("W2", "landscape", "Intended subject: menus, escort cards, seating, and signage. Real photograph not provided.", "Placeholder W2. Not a photograph of finished work.", photo="W2-01-menus", depth=depth, mode=mode)}
        <h2>Day-of details</h2>
      </a>
    </div>
  </div>
</section>
<section class="section band">
  <div class="wrap grid">
    <div class="span-6">
      <h2>Invitations</h2>
      <p>Invitation suites live in the stationery section.</p>
      <a class="btn btn-secondary" href="{href(depth, "stationery/invitations", mode)}">Wedding invitations</a>
    </div>
    <div class="span-6">{ph("S1", "landscape", "Intended subject: an invitation suite. Real photograph not provided.", "Placeholder S1. Not a photograph of finished work.", photo="S1-01", depth=depth, mode=mode)}</div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_favors(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Weddings", "weddings"), ("Custom favors", None)]
    ids = ["lead-time", "handmade", "custom"]
    frames = [
        ph("W1", "square", "Intended subject: wedding favors, flat lay. Real photograph not provided.", piece_caption("Wedding favors"), photo="W1-01", depth=depth, mode=mode),
        ph("W1", "square", "Intended subject: a wedding favor detail. Real photograph not provided.", piece_caption("Wedding favor detail"), photo="W1-02", depth=depth, mode=mode),
    ]
    extra = []
    for slot, _cat, piece in PORTFOLIO[:4]:
        extra.append(
            f'<div class="span-4">{ph(slot, "square", "Real photograph not provided. Intended subject: " + piece + ".", piece_caption(piece), photo=slot, depth=depth, mode=mode)}</div>'
        )
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Wedding favors are personalized and made by hand for one celebration. Engraving and new kinds of custom pieces are not offered on this site.</p>
    <div class="grid">
      <div class="span-6">{frames[0]}</div>
      <div class="span-6">{frames[1]}</div>
      {"".join(extra)}
    </div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_day_of(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Weddings", "weddings"), ("Day-of details", None)]
    ids = ["seating-include", "seating", "handmade"]
    subs = [
        ("Menus", "Menus designed as a custom paper piece for the celebration.", "W2 frame 1 of 5", "W2-01-menus"),
        ("Escort cards", "Escort cards to help guests find their place.", "W2 frame 2 of 5", "W2-02-escort"),
        ("Table numbers", "Table numbers designed with the rest of the day-of paper.", "W2 frame 3 of 5", "W2-03-table-numbers"),
        ("Seating charts", "Seating charts designed and made by hand for the celebration.", "W2 frame 4 of 5", "W2-04-seating"),
        ("Day-of signage", "Signage for the celebration, designed with the other paper details.", "W2 frame 5 of 5", "W2-05-signage"),
    ]
    blocks = []
    for title, text, slot, photo_id in subs:
        blocks.append(
            f"""
<div class="span-6">
  <h2>{esc(title)}</h2>
  <p>{esc(text)}</p>
  {ph(slot, "landscape", "Intended subject: " + title.lower() + ". Real photograph not provided. The W2 set asks for five photographs.", piece_caption(title), photo=photo_id, depth=depth, mode=mode)}
</div>
"""
        )
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <div class="grid">{"".join(blocks)}</div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_mitzvah(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Bar & bat mitzvahs", None)]
    ids = ["favor-ideas", "custom", "areas"]
    frames = []
    for index in range(1, 4):
        frames.append(
            f'<div class="span-4">{ph(f"M1 frame {index} of 3", "landscape", "Intended subject: a bar or bat mitzvah table or display. Real photograph not provided.", piece_caption("Bar and bat mitzvah table or display"), photo=f"M1-0{index}", depth=depth, mode=mode)}</div>'
        )
    return f"""
<section class="hero">
  {ph("M1", "hero", "Intended subject: a bar or bat mitzvah display. Real photograph not provided.", "Placeholder M1. Not a photograph of finished work.", photo="M1-01", depth=depth, mode=mode)}
  <div class="wrap hero-copy">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="sub">Personalized favors and day-of paper designed around the guest of honor.</p>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="grid">{"".join(frames)}</div>
    <div class="actions">
      <a class="btn btn-secondary" href="{href(depth, "bar-bat-mitzvahs/favors", mode)}">Favors</a>
      <a class="btn btn-secondary" href="{href(depth, "bar-bat-mitzvahs/day-of-details", mode)}">Day-of details</a>
      <a class="btn btn-secondary" href="{href(depth, "stationery", mode)}">Stationery</a>
    </div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_mitzvah_favors(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Bar & bat mitzvahs", "bar-bat-mitzvahs"), ("Favors", None)]
    ids = ["favor-ideas", "handmade", "lead-time"]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Favors for a bar or bat mitzvah are personalized around the guest of honor and made by hand. This page does not list a catalog of finished products.</p>
    <div class="grid">
      <div class="span-6">{ph("M2 frame 1 of 2", "square", "Intended subject: mitzvah favors, flat lay. Real photograph not provided.", piece_caption("Bar and bat mitzvah favors"), photo="M2-01", depth=depth, mode=mode)}</div>
      <div class="span-6">{ph("M2 frame 2 of 2", "square", "Intended subject: a mitzvah favor detail. Real photograph not provided.", piece_caption("Bar and bat mitzvah favor detail"), photo="M2-02", depth=depth, mode=mode)}</div>
    </div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_mitzvah_day(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Bar & bat mitzvahs", "bar-bat-mitzvahs"), ("Day-of details", None)]
    ids = ["seating", "seating-include", "areas"]
    frames = []
    subjects = ["menus", "escort cards", "a seating chart"]
    for index, subject in enumerate(subjects, start=1):
        frames.append(
            f'<div class="span-4"><h2>{esc(subject.capitalize())}</h2>{ph(f"M3 frame {index} of 3", "landscape", "Intended subject: " + subject + ". Real photograph not provided.", piece_caption("Bar and bat mitzvah " + subject), photo=f"M3-0{index}", depth=depth, mode=mode)}</div>'
        )
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <div class="grid">{"".join(frames)}</div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_celebrations(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Other celebrations", None)]
    ids = ["areas", "custom", "handmade"]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <p class="kicker">In the background</p>
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Bridal showers and other celebrations are part of the work, beside weddings and bar and bat mitzvahs. They are not the center of the site.</p>
    <div class="grid">
      <div class="span-6">{ph("R1 frame 1 of 2", "landscape", "Intended subject: a bridal shower table. Real photograph not provided.", piece_caption("Bridal shower favors and paper"), photo="R1-01", depth=depth, mode=mode)}</div>
      <div class="span-6">
        <h2>Bridal showers</h2>
        <p>Favors and paper details for a bridal shower.</p>
        <a class="btn btn-secondary" href="{href(depth, "celebrations/bridal-showers", mode)}">Bridal showers</a>
      </div>
    </div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_bridal(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Other celebrations", "celebrations"), ("Bridal showers", None)]
    ids = ["custom", "handmade", "lead-time"]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <p class="kicker">In the background</p>
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Custom favors and paper details for a bridal shower, designed and made by hand.</p>
    <div class="grid">
      <div class="span-6">{ph("R1 frame 1 of 2", "landscape", "Intended subject: bridal shower favors. Real photograph not provided.", piece_caption("Bridal shower favors"), photo="R1-01", depth=depth, mode=mode)}</div>
      <div class="span-6">{ph("R1 frame 2 of 2", "landscape", "Intended subject: bridal shower paper details. Real photograph not provided.", piece_caption("Bridal shower paper details"), photo="R1-02", depth=depth, mode=mode)}</div>
    </div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_stationery(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Stationery", None)]
    ids = ["prices", "custom", "handmade"]
    return f"""
<section class="hero">
  {ph("S1", "hero", "Intended subject: an invitation suite, flat lay. Real photograph not provided.", "Placeholder S1. Not a photograph of finished work.", photo="S1-01", depth=depth, mode=mode)}
  <div class="wrap hero-copy">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="sub">Invitations and day-of paper, designed in-house and finished by hand.</p>
  </div>
</section>
<section class="section">
  <div class="wrap grid">
    <div class="span-6">
      <a class="card-link" href="{href(depth, "stationery/invitations", mode)}">
        {ph("S1", "landscape", "Intended subject: invitations. Real photograph not provided.", "Placeholder S1. Not a photograph of finished work.", photo="S1-01", depth=depth, mode=mode)}
        <h2>Invitations</h2>
      </a>
    </div>
    <div class="span-6">
      <a class="card-link" href="{href(depth, "stationery/portfolio", mode)}">
        {ph("S3", "landscape", "Intended subject: stationery pieces. Real photograph not provided.", "Placeholder S3. Not a photograph of finished work.", photo="S3-01", depth=depth, mode=mode)}
        <h2>Portfolio</h2>
      </a>
    </div>
  </div>
</section>
<section class="section band">
  <div class="wrap">
    <h2>Pricing by custom quote.</h2>
    <p>Prices are not published. There is no starting price on this page.</p>
    <a class="btn btn-primary" href="{href(depth, "stationery/inquiry", mode)}">Start a stationery inquiry</a>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
"""


def render_invitations(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Stationery", "stationery"), ("Invitations", None)]
    ids = ["invitations-lead", "handmade", "prices"]
    frames = [
        ph("S1 frame 1 of 2", "square", "Intended subject: an invitation suite. Real photograph not provided.", piece_caption("Invitation suite"), photo="S1-01", depth=depth, mode=mode),
        ph("S1 frame 2 of 2", "square", "Intended subject: an invitation suite detail. Real photograph not provided.", piece_caption("Invitation suite detail"), photo="S1-02", depth=depth, mode=mode),
    ]
    extra = []
    for slot, _cat, piece in STATIONERY_FRAMES[:4]:
        extra.append(f'<div class="span-4">{ph(slot, "square", "Real photograph not provided. Intended subject: " + piece + ".", piece_caption(piece), photo=slot, depth=depth, mode=mode)}</div>')
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Invitation suites are designed and finished by hand. A lead time for invitations is not published on this page.</p>
    <div class="grid">
      <div class="span-6">{frames[0]}</div>
      <div class="span-6">{frames[1]}</div>
      {"".join(extra)}
    </div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode, target="stationery/inquiry", label="Start a stationery inquiry")}
"""


def render_stationery_portfolio(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Stationery", "stationery"), ("Portfolio", None)]
    filters = [
        ("invitations", "Invitations"),
        ("menus", "Menus"),
        ("cards", "Cards"),
        ("signage", "Signage"),
    ]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Eight labeled frames stand in for stationery photographs that are not published yet. A caption names the piece, not an event, and no photographer is credited.</p>
    {filter_gallery(STATIONERY_FRAMES, filters, depth, mode)}
  </div>
</section>
{cta(depth, mode, target="stationery/inquiry", label="Start a stationery inquiry")}
"""


def render_portfolio(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Portfolio", None)]
    filters = [("weddings", "Weddings"), ("mitzvahs", "Mitzvahs"), ("showers", "Showers")]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Twelve labeled frames stand in for photographs that are not published yet. Captions name pieces by Joyful Creations LI. They do not call an event a production of the studio. No client or venue is named.</p>
    {filter_gallery(PORTFOLIO, filters, depth, mode)}
  </div>
</section>
{cta(depth, mode)}
"""


def render_process(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Process", None)]
    ids = ["lead-time", "payments", "deliver"]
    lead = next(item["a"] for item in faq["items"] if item["id"] == "lead-time")
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    {steps([
        ("Consultation", "The conversation starts with the consultation form or an email. This review build does not send the form."),
        ("Design proposal", "The studio proposes pieces for the celebration. This is not a catalog order."),
        ("Revisions", "Revisions are part of the conversation. A revision count is not published."),
        ("Handmade production", "Pieces the studio takes on are made by hand."),
        ("Handoff", "Delivery, pickup, or on-site setup is not confirmed on this website."),
    ], five=True)}
    <h2>Lead time</h2>
    <p>{esc(lead)}</p>
    <h2>Payment</h2>
    <p>Payment methods are not published on this website. This site does not take payment, deposits, or checkout. A change and cancellation policy is not published, so online payment is not offered.</p>
    <div class="grid">
      <div class="span-4">{ph("P1 frame 1 of 3", "landscape", "Intended subject: design on a screen. Real photograph not provided.", "Placeholder P1. Not a photograph.", photo="P1-01-diseno", depth=depth, mode=mode)}</div>
      <div class="span-4">{ph("P1 frame 2 of 3", "landscape", "Intended subject: handmade assembly. Real photograph not provided.", "Placeholder P1. Not a photograph.", photo="P1-02-armado", depth=depth, mode=mode)}</div>
      <div class="span-4">{ph("P1 frame 3 of 3", "landscape", "Intended subject: pieces prepared to leave the studio. Delivery is not confirmed. Real photograph not provided.", "Placeholder P1. Not a photograph, and not a delivery claim.", photo="P1-03-empacado", depth=depth, mode=mode)}</div>
    </div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_areas_hub(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Service areas", None)]
    ids = ["areas", "deliver", "prices"]
    links = [
        ("Long Island", "service-areas/long-island"),
        ("New York City", "service-areas/nyc"),
        ("New Jersey", "service-areas/new-jersey"),
        ("Connecticut", "service-areas/connecticut"),
    ]
    items = "".join(f'<li><a href="{href(depth, target, mode)}">{esc(label)}</a></li>' for label, target in links)
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Joyful Creations LI serves celebrations in New York, New Jersey, and Connecticut, including Long Island and New York City. These pages do not list venues or local events. Delivery and on-site setup are not confirmed.</p>
    <ul class="area-list">{items}</ul>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_area(page, faq, mode):
    depth = depth_of(page["path"])
    name = AREA_NAMES[page["path"]]
    crumbs = [("Home", ""), ("Service areas", "service-areas"), (name, None)]
    ids = ["areas", "deliver", "prices"]
    frames = []
    for slot, _cat, piece in (PORTFOLIO[0], PORTFOLIO[4], PORTFOLIO[8]):
        frames.append(
            f'<div class="span-4">{ph(slot + " · " + name, "landscape", "Real photograph not provided. This is not a venue and not a local event in " + name + ".", "Placeholder for " + piece + " by Joyful Creations LI. Not an event in " + name + ".", photo=slot, depth=depth, mode=mode)}</div>'
        )
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Joyful Creations LI serves celebrations in {esc(name)}. This page does not list venues or local events. Delivery and on-site setup are not confirmed here.</p>
    <div class="grid">{"".join(frames)}</div>
  </div>
</section>
{faq_section(depth, faq, ids, mode)}
{cta(depth, mode)}
"""


def render_faq(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("FAQ", None)]
    ids = [item["id"] for item in faq["items"] if item["hub"]]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Answers are short on purpose. Timing is not a guarantee, prices are not listed, and payment is not taken on this website.</p>
    {faq_html(faq, ids)}
  </div>
</section>
{cta(depth, mode)}
"""


def render_quote(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Request a consultation", None)]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <a class="logo-lockup" href="{href(depth, "", mode)}">
      <img src="{asset(depth, "marca/logo-joyful-creations.png", mode)}" width="1920" height="1280" alt="Joyful Creations logo">
    </a>
    <div class="grid">
      <div class="span-5">
        <h1>{esc(page["h1"])}</h1>
        <p>Tell us about your celebration. Fields marked with * are required. There is no budget field and no payment.</p>
        {ph("H3", "landscape", "Intended subject: a paper detail beside the form. Real photograph not provided.", "Placeholder H3. Not a photograph of finished work.", photo="H3-01", depth=depth, mode=mode)}
      </div>
      <div class="span-7">
        {quote_form(depth, mode)}
      </div>
    </div>
  </div>
</section>
"""


def render_inquiry(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Stationery", "stationery"), ("Inquiry", None)]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <a class="logo-lockup" href="{href(depth, "", mode)}">
      <img src="{asset(depth, "marca/logo-joyful-creations.png", mode)}" width="1920" height="1280" alt="Joyful Creations logo">
    </a>
    <h1>{esc(page["h1"])}</h1>
    <p class="prose">Tell us about the paper you need. Fields marked with * are required. This is not a checkout.</p>
    {inquiry_form(depth, mode)}
  </div>
</section>
"""


def render_contact(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Contact", None)]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <p>Email us at <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
    <p>A phone number is not published. A street address is not published.</p>
    <p><a class="btn btn-primary" href="{href(depth, "quote", mode)}">Request a consultation</a></p>
    <p>The consultation form on this review build does not send.</p>
  </div>
</section>
"""


def render_privacy(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Privacy", None)]
    return f"""
<section class="section">
  <div class="wrap prose">
    {crumbs_html(depth, crumbs, mode)}
    <h1>{esc(page["h1"])}</h1>
    <div class="pending"><p>[PENDIENTE] This page explains the forms in plain language. It is not an approved legal policy.</p></div>
    <h2>What the consultation form asks</h2>
    <p>Full name, email, optional phone, event type, event date, city and state, optional guest count, the pieces you are considering, optional notes, an optional note about how you heard of the studio, and consent to be emailed about the request. It does not ask for a budget, a tax identifier, or a document.</p>
    <h2>What the stationery form asks</h2>
    <p>Full name, email, piece type, approximate quantity, the date you need the pieces, an optional finish, optional inspiration images, optional notes, and the same email consent. Images are not uploaded in this review build. A file size limit is not set.</p>
    <h2>Why those details would be used</h2>
    <p>They would be used to reply by email about the request. The mailbox named for a future send is {EMAIL}. This review build does not transmit the form, does not store it on a server, and does not share it.</p>
    <h2>What stays in the browser</h2>
    <p>A draft may be kept in this browser's session storage so a refresh does not clear the fields. Campaign parameters from the link, if they match the expected pattern, are kept the same way and copied into hidden fields. This site does not set tracking cookies.</p>
    <h2>What this site does not run</h2>
    <p>No analytics tool is installed. Advertising pixels are not loaded. The pixel slots in the page head are empty.</p>
    <p><a href="{href(depth, "contact", mode)}">Contact</a></p>
  </div>
</section>
"""


def render_thanks(page, faq, mode):
    depth = depth_of(page["path"])
    crumbs = [("Home", ""), ("Thank you", None)]
    return f"""
<section class="section">
  <div class="wrap">
    {crumbs_html(depth, crumbs, mode)}
    <a class="logo-lockup" href="{href(depth, "", mode)}">
      <img src="{asset(depth, "marca/logo-joyful-creations.png", mode)}" width="1920" height="1280" alt="Joyful Creations logo">
    </a>
    <h1>{esc(page["h1"])}</h1>
    <div class="review-note" id="review-note" tabindex="-1">
      <p class="kicker">Review build</p>
      <p>Nothing was sent. This page does not mean a message arrived. There is no form endpoint, and nobody was emailed.</p>
    </div>
    <p>Thank you — we'll review your request and reply by email.</p>
    <p>That sentence is the wording prepared for a future send. No reply time is promised.</p>
    <p><a href="mailto:{EMAIL}">{EMAIL}</a></p>
    <p><a href="{href(depth, "", mode)}">Back to the home page</a></p>
  </div>
</section>
"""


def render_404():
    page = {
        "path": "404",
        "title": "Page Not Found | Joyful Creations LI",
        "description": "This page is not on the Joyful Creations LI website.",
        "h1": "This page is not available.",
        "noindex": True,
    }
    main = f"""
<section class="section">
  <div class="wrap">
    <h1>{esc(page["h1"])}</h1>
    <p>The link may be mistyped, or the page may be unpublished.</p>
    <ul class="link-row">
      <li><a href="/" data-root="">Home</a></li>
      <li><a href="/weddings/" data-root="weddings/">Weddings</a></li>
      <li><a href="/bar-bat-mitzvahs/" data-root="bar-bat-mitzvahs/">Bar &amp; bat mitzvahs</a></li>
      <li><a href="/stationery/" data-root="stationery/">Stationery</a></li>
      <li><a href="/contact/" data-root="contact/">Contact</a></li>
    </ul>
  </div>
</section>
"""
    return page, main


RENDERERS = {
    "": render_home,
    "about": render_about,
    "weddings": render_weddings,
    "weddings/custom-favors": render_favors,
    "weddings/day-of-details": render_day_of,
    "bar-bat-mitzvahs": render_mitzvah,
    "bar-bat-mitzvahs/favors": render_mitzvah_favors,
    "bar-bat-mitzvahs/day-of-details": render_mitzvah_day,
    "celebrations": render_celebrations,
    "celebrations/bridal-showers": render_bridal,
    "stationery": render_stationery,
    "stationery/invitations": render_invitations,
    "stationery/portfolio": render_stationery_portfolio,
    "stationery/inquiry": render_inquiry,
    "portfolio": render_portfolio,
    "process": render_process,
    "service-areas": render_areas_hub,
    "service-areas/long-island": render_area,
    "service-areas/nyc": render_area,
    "service-areas/new-jersey": render_area,
    "service-areas/connecticut": render_area,
    "faq": render_faq,
    "quote": render_quote,
    "contact": render_contact,
    "privacy": render_privacy,
    "thank-you": render_thanks,
}

FAQ_IDS = {
    "weddings": ["lead-time", "custom", "seating"],
    "weddings/custom-favors": ["lead-time", "handmade", "custom"],
    "weddings/day-of-details": ["seating-include", "seating", "handmade"],
    "bar-bat-mitzvahs": ["favor-ideas", "custom", "areas"],
    "bar-bat-mitzvahs/favors": ["favor-ideas", "handmade", "lead-time"],
    "bar-bat-mitzvahs/day-of-details": ["seating", "seating-include", "areas"],
    "celebrations": ["areas", "custom", "handmade"],
    "celebrations/bridal-showers": ["custom", "handmade", "lead-time"],
    "stationery": ["prices", "custom", "handmade"],
    "stationery/invitations": ["invitations-lead", "handmade", "prices"],
    "process": ["lead-time", "payments", "deliver"],
    "service-areas": ["areas", "deliver", "prices"],
    "service-areas/long-island": ["areas", "deliver", "prices"],
    "service-areas/nyc": ["areas", "deliver", "prices"],
    "service-areas/new-jersey": ["areas", "deliver", "prices"],
    "service-areas/connecticut": ["areas", "deliver", "prices"],
    "faq": None,
}

COLLECTION_PATHS = {"portfolio", "stationery/portfolio", "stationery"}
SERVICE_PATHS = {
    "weddings",
    "weddings/custom-favors",
    "weddings/day-of-details",
    "bar-bat-mitzvahs",
    "bar-bat-mitzvahs/favors",
    "bar-bat-mitzvahs/day-of-details",
    "celebrations",
    "celebrations/bridal-showers",
    "stationery",
    "stationery/invitations",
    "service-areas",
    "service-areas/long-island",
    "service-areas/nyc",
    "service-areas/new-jersey",
    "service-areas/connecticut",
}


def schemas_for(page: dict, faq: dict) -> list:
    path = page["path"]
    if path == "":
        return home_schema()
    if path == "about":
        person = {"@type": "Person", "name": "Jonah"}
        return [
            {"@type": "AboutPage", "name": page["title"], "description": page["description"], "mainEntity": person},
            person,
            crumb_schema([("Home", ""), ("About", None)]),
        ]
    nodes = []
    if path in SERVICE_PATHS:
        area = AREA_NAMES.get(path)
        nodes.append(service_schema(page, area))
    if path in COLLECTION_PATHS:
        nodes.append({"@type": "CollectionPage", "name": page["title"], "description": page["description"]})
    if path in {"quote", "contact", "stationery/inquiry"}:
        nodes.append(
            {
                "@type": "ContactPage",
                "name": page["title"],
                "description": page["description"],
                "email": EMAIL,
            }
        )
    if path == "faq":
        ids = [item["id"] for item in faq["items"] if item["hub"]]
        nodes.append(faq_schema(faq, ids))
    elif path in FAQ_IDS and FAQ_IDS[path]:
        nodes.append(faq_schema(faq, FAQ_IDS[path]))
    if path == "portfolio":
        nodes.extend(image_schemas(PORTFOLIO))
    if path == "stationery/portfolio":
        nodes.extend(image_schemas(STATIONERY_FRAMES))
    if path == "404":
        nodes.append({"@type": "WebPage", "name": page["title"]})
    if not nodes:
        nodes.append({"@type": "WebPage", "name": page["title"], "description": page["description"], "inLanguage": "en"})
    return nodes


def check_logo() -> None:
    logo = ROOT / "marca" / "logo-joyful-creations.png"
    digest = hashlib.sha256(logo.read_bytes()).hexdigest()
    if digest != LOGO_SHA or logo.stat().st_size != 503213:
        raise SystemExit("Official logo hash or size does not match. The file must not be redrawn.")


def check_faq(faq: dict) -> None:
    for item in faq["items"]:
        count = words(item["a"])
        if not 40 <= count <= 60:
            raise SystemExit(f"FAQ {item['id']} is {count} words, expected 40–60.")


def h1_text(document: str) -> list[str]:
    found = re.findall(r"<h1>(.*?)</h1>", document, flags=re.S)
    return [html.unescape(re.sub(r"<[^>]+>", "", item)).strip() for item in found]


def write_sitemap(paths: list[str]) -> None:
    urls = []
    for path in paths:
        loc = "/" if not path else f"/{path}/"
        urls.append(f"  <url><loc>{loc}</loc></url>")
    body = """<?xml version="1.0" encoding="UTF-8"?>
<!-- Public host is not set. Loc values are site paths, not absolute URLs. -->
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
""".format(urls="\n".join(urls))
    (ROOT / "sitemap.xml").write_text(body, encoding="utf-8")


def local_links_resolve(page_path: str, document: str) -> None:
    if page_path == "404":
        return
    depth = depth_of(page_path)
    base = ROOT if depth == 0 else ROOT.joinpath(*page_path.split("/"))
    for match in re.findall(r'href="([^"]+)"', document):
        if match.startswith(("mailto:", "#", "http://", "https://")):
            continue
        target = (base / match).resolve()
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            raise SystemExit(f"Broken link on /{page_path or ''}: {match} -> {target}")


def main() -> None:
    check_logo()
    pages = load_json("pages.json")
    faq = load_json("faq.json")
    listings = load_json("listings.json")
    check_faq(faq)
    paths = [page["path"] for page in pages]
    if set(paths) != set(RENDERERS):
        missing = set(RENDERERS) - set(paths)
        extra = set(paths) - set(RENDERERS)
        raise SystemExit(f"Page map mismatch. Missing renderers {missing}. Extra paths {extra}.")
    written = []
    for page in pages:
        renderer = RENDERERS[page["path"]]
        main_html = renderer(page, faq, "relative")
        document = shell(page, main_html, schemas_for(page, faq), listings, "relative")
        found = h1_text(document)
        if found != [page["h1"]]:
            raise SystemExit(f"H1 mismatch on {page['path']}: {found!r} != {page['h1']!r}")
        destination = ROOT / "index.html" if not page["path"] else ROOT / page["path"] / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8")
        written.append(page["path"])
        if len(page["title"]) > 60:
            print(f"title {len(page['title'])} chars: {page['path']}")
    page_404, main_404 = render_404()
    document_404 = shell(page_404, main_404, schemas_for(page_404, faq), listings, "root")
    (ROOT / "404.html").write_text(document_404, encoding="utf-8")
    for page in pages:
        document = (ROOT / "index.html" if not page["path"] else ROOT / page["path"] / "index.html").read_text(encoding="utf-8")
        local_links_resolve(page["path"], document)
    write_sitemap(written)
    blocked = [
        ROOT / "celebrations" / "corporate" / "index.html",
        ROOT / "stationery" / "hot-foil" / "index.html",
        ROOT / "reviews" / "index.html",
    ]
    for path in blocked:
        if path.exists():
            raise SystemExit(f"Blocked page was written: {path}")
    print(f"Wrote {len(written)} pages + 404.")


if __name__ == "__main__":
    main()
