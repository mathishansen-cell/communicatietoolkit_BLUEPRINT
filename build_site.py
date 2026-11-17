"""Build the public GitHub Pages site (index.html + images/) from the Claude artifact.

Usage: python3 build_site.py <artifact index.html> <folder with downloaded assets>

The artifact stays the place where you edit. This script copies its content,
swaps the artifact's uploaded images (/_blob/<id>) for files in images/, and
turns off edit mode so the public page is read-only. Downloads work there.
"""
import json, re, shutil, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
STATE_RE = re.compile(r'(<script type="application/json" id="state">)(.*?)(</script>)', re.S)


def slug(text):
    text = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "beeld"


def main(artifact_html, asset_dir):
    live = Path(artifact_html).read_text(encoding="utf-8")
    state = json.loads(STATE_RE.search(live).group(2))
    assets = {p.stem: p for p in Path(asset_dir).iterdir() if p.is_file()}
    out_dir = ROOT / "images"
    out_dir.mkdir(exist_ok=True)
    used = set()

    def localize(src, name):
        m = re.fullmatch(r"/_blob/([0-9a-f]{32})", src or "")
        if not m:
            return src
        asset = assets.get(m.group(1))
        if not asset:
            sys.exit(f"Missing downloaded asset for {name}: {m.group(1)}")
        base, n = slug(name), 1
        fname = f"{base}{asset.suffix}"
        while fname in used:
            n += 1
            fname = f"{base}-{n}{asset.suffix}"
        used.add(fname)
        shutil.copyfile(asset, out_dir / fname)
        return f"images/{fname}"

    state["header"]["logo"] = localize(state["header"].get("logo"), "sinc-logo")
    for section in state["sections"]:
        for block in section["blocks"]:
            if block["type"] == "image":
                block["src"] = localize(block.get("src"), block.get("title") or "beeld")

    for old in out_dir.iterdir():
        if old.name not in used:
            old.unlink()

    # Keep the editable copy in sync with what was saved in the artifact.
    (ROOT / "Toolkit V2.html").write_text(
        live.split("<body>", 1)[1].rsplit("</body>", 1)[0], encoding="utf-8")

    page = (ROOT / "Toolkit V2.html").read_text(encoding="utf-8")
    page = page.replace("var canEditPage=!hasRuntime", "var canEditPage=false", 1)
    data = json.dumps(state, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    page = STATE_RE.sub(lambda m: m.group(1) + data + m.group(3), page, count=1)
    head = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n</head>\n<body>\n'
    (ROOT / "index.html").write_text(head + page + "\n</body>\n</html>\n", encoding="utf-8")
    print("Built index.html with", len(used), "images:", ", ".join(sorted(used)))


if __name__ == "__main__":
    main(*sys.argv[1:3])
