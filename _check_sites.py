import pathlib, json, urllib.parse
for f in pathlib.Path("data/sites").iterdir():
    if f.suffix == ".json":
        d = json.loads(f.read_text("utf-8"))
        decoded = urllib.parse.unquote(urllib.parse.unquote(f.stem))
        print(f"file: {f.name}")
        print(f"  decoded stem: {decoded}")
        print(f"  site_name: {d.get('site_name', 'MISSING')}")
        print(f"  top keys: {list(d.keys())[:8]}")
        print()
