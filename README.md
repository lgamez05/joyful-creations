# Joyful Creations LI

Where every celebration tells your story

Static review build of the Joyful Creations LI website. The public pages are in English.

This branch is for review. It is not a public launch. It does not change DNS, add a CNAME, or change GitHub Pages settings.

Consultation and stationery forms do not send. There is no form service and no analytics. Real event photographs are not published. Empty frames are marked [PENDIENTE].

## View locally

```bash
python3 tools/build_site.py
python3 -m http.server 8765
```

Open http://127.0.0.1:8765/

Page copy and routes come from `content/`. `tools/build_site.py` writes the HTML. The service worker file is not registered.
