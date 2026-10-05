"""Verify the claims map: named files/symbols exist, explorer is stdlib-only, towerops.py unchanged vs e8fa18e.
Usage: python presentation/check_claims.py (from repo root). Exit 0 = ok."""
import ast
import pathlib
import re
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent.parent
text = (root / "presentation" / "claims-map.md").read_text()
bad = []
for f in sorted(set(re.findall(r"`((?:web/)?[A-Za-z_]+\.(?:py|js|html|css|md))`", text))):
    if not (root / f).exists() and not (root / "presentation" / f).exists():
        bad.append(f"missing file {f}")
src = {p: (root / p).read_text() for p in ("towerops.py", "scenarios.py", "explorer.py", "strands_adapter.py", "test_explorer.py")}
for sym in re.findall(r"`([A-Za-z_][A-Za-z_.]*)`", text):
    last = sym.split(".")[-1]
    if last in ("py", "js", "md", "html", "css"): continue
    if (
        ("_" in last or last[0].isupper())
        and not any(re.search(rf"\b{re.escape(last)}\b", s) for s in src.values())
        and not (root / "web" / "app.js").read_text().count(last)
    ):
        bad.append(f"symbol not found: {sym}")
stdlib = set(sys.stdlib_module_names)
for mod in ("explorer.py", "scenarios.py", "towerops.py"):
    for n in ast.walk(ast.parse(src[mod])):
        names = [a.name.split(".")[0] for a in n.names] if isinstance(n, ast.Import) else ([n.module.split(".")[0]] if isinstance(n, ast.ImportFrom) and n.module else [])
        for m in names:
            if m not in stdlib and m not in ("towerops", "scenarios", "explorer"):
                bad.append(f"{mod} imports non-stdlib {m}")
r = subprocess.run(["git", "diff", "--quiet", "e8fa18e", "HEAD", "--", "towerops.py"], cwd=root, check=False)
if r.returncode not in (0,):
    bad.append("towerops.py differs from e8fa18e (or e8fa18e not fetched)")
print("\n".join(bad) if bad else "claims-map check OK")
sys.exit(1 if bad else 0)
