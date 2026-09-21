"""Writes the OpenAPI document that apps/web generates its client from."""

import json
from pathlib import Path

from app.main import create_app

out = Path(__file__).resolve().parent.parent / "openapi.json"
out.write_text(json.dumps(create_app(seed=False).openapi(), indent=2) + "\n")
print(f"wrote {out}")
