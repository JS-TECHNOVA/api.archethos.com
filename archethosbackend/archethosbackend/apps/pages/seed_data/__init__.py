"""
The site's launch content.

`site_data.json` is a machine dump of the frontend's `src/data/*.js` modules,
produced by `dump.mjs` in this directory. It is generated rather than typed out
because those files are the studio's copy — 24 gallery captions, 7 project
narratives, 5 service descriptions — and a hand transcription of that would
introduce errors nobody would notice until the words were live.

Regenerate after the studio edits the frontend data files:

    node archethosbackend/apps/pages/seed_data/dump.mjs

`pages.py` holds what the dump cannot reach: the copy that lives in the page
components themselves rather than in a data module.

⚠️ Two things in here are flagged placeholders in the source and must stay
flagged. The photography is licensed stock standing in for the studio's own
work, seeded as `EXTERNAL` assets pointing at Unsplash. Two of the four headline
figures ("Projects delivered", "Client satisfaction") are unverified, and are
seeded as drafts so they cannot reach the site by accident.
"""

import json
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent


def load():
    """The frontend data dump, as plain dictionaries."""
    return json.loads((SEED_DIR / "site_data.json").read_text(encoding="utf-8"))
