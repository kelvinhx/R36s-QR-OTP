import os
import hashlib
import json

def sha256sum(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sh_path = os.path.join(base_dir, "R36S_WebFileManager.sh")
    
    sh_size = os.path.getsize(sh_path)
    sh_sha = sha256sum(sh_path)
    with open(sh_path, "r", encoding="utf-8", errors="ignore") as f:
        sh_lines = len(f.readlines())

    sources = ["server.py", "ui.html", "controls.gptk", "build_standalone.py", "test_backend.py"]
    source_stats = {}
    for s in sources:
        p = os.path.join(base_dir, s)
        if os.path.exists(p):
            size = os.path.getsize(p)
            sha = sha256sum(p)
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                lines = len(f.readlines())
            source_stats[s] = {"size": size, "lines": lines, "sha256": sha}

    assets_base = os.path.join(base_dir, "assets")
    asset_count = 0
    categories = {}
    if os.path.isdir(assets_base):
        for root, dirs, files in os.walk(assets_base):
            for file in files:
                asset_count += 1
                cat = os.path.relpath(root, assets_base).split(os.sep)[0]
                if cat == ".":
                    cat = "root"
                categories[cat] = categories.get(cat, 0) + 1

    print(json.dumps({
        "sh": {"size": sh_size, "lines": sh_lines, "sha256": sh_sha},
        "sources": source_stats,
        "assets_total": asset_count,
        "categories": categories
    }, indent=2))

if __name__ == "__main__":
    main()
