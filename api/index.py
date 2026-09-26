"""Vercel entry point: exposes the FastAPI app as `app`.

Configuration comes from Vercel environment variables (DATABASE_URL, CONTACT_HASH_PEPPER,
SMS_WEBHOOK_SECRET, INLINE_REPLIES=true, WHATSAPP_*). Replies are sent inside the request
(`INLINE_REPLIES`) because Vercel may freeze the function once it has responded.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("REFERENCE_DIR", str(ROOT / "data" / "reference"))
os.environ.setdefault("INLINE_REPLIES", "true")

from kisan.app import create_app  # noqa: E402

app = create_app()
