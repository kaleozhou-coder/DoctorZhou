"""Retrieve only manifest-listed official example bytes; enforce size cap and pinned hashes."""
import hashlib, io, json, pathlib, urllib.request, zipfile
root = pathlib.Path(__file__).resolve().parent
cache = {}
for item in json.loads((root / "manifest.json").read_text()):
    url = item["source_url"]
    if url not in cache:
        with urllib.request.urlopen(url, timeout=45) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise RuntimeError("Source exceeds 2MB cap: " + url)
        cache[url] = body
    body = cache[url]
    if item.get("archive_member"):
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            info = archive.getinfo(item["archive_member"])
            if info.file_size > 2_000_000:
                raise RuntimeError("Member exceeds size cap")
            body = archive.read(info)
    if hashlib.sha256(body).hexdigest() != item["sha256"]:
        raise RuntimeError("Source changed: " + item["path"])
    target = root / item["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    print("Verified", item["path"])
