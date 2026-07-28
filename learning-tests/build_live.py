"""Does the build spine's India filter hold on live Greenhouse payloads? — T5.1

The fixtures prove the emit path. What they cannot prove is the one assumption
the spine makes about a *real* role object: that `location.name` is always there
and always a string. `build.build` unwraps it as `(role.get("location") or
{}).get("name")`, and if live boards carry roles with a null or differently
shaped location, those roles are silently not-India — an undercount that looks
exactly like a correct answer.

So: probe the five FINDINGS boards for real, count what the spine would list,
and report every role whose location isn't the shape assumed.

    .venv/bin/python learning-tests/build_live.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.greenhouse import probe  # noqa: E402
from src.india import is_india  # noqa: E402
from src.outcomes import Outcome  # noqa: E402

SLUGS = ("databricks", "anthropic", "gleanwork", "togetherai", "figma")

listed = 0
for slug in SLUGS:
    roles = probe(slug)
    if isinstance(roles, Outcome):
        print(f"{slug:12} {roles.value}")
        continue

    odd = [r.get("id") for r in roles if not isinstance(r.get("location"), dict)]
    missing = [r.get("id") for r in roles if isinstance(r.get("location"), dict)
               and not isinstance(r["location"].get("name"), str)]
    india = [r for r in roles if is_india((r.get("location") or {}).get("name"))]

    listed += bool(india)
    print(
        f"{slug:12} {len(roles):4d} roles  {len(india):4d} India  "
        f"location-not-a-dict: {len(odd)}  name-not-a-string: {len(missing)}"
    )
    for role_id in (odd + missing)[:3]:
        print(f"             ^ role {role_id}")

print(f"\n{listed}/{len(SLUGS)} boards would produce a listed row.")
