#!/usr/bin/env python3
"""Inspect a public QEC archive without fetching unselected large members."""

import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile


ARCHIVES = {
    "willow_stability_2026": {
        "url": "https://zenodo.org/api/records/24142014/files/stability_paper_data.zip/content",
        "bytes": 42880786814,
        "provider_md5_not_rehashed": "6a5e3612e0c2e79437ffc71428917c35",
    },
    "sycamore_leakage_2022": {
        "url": "https://zenodo.org/records/7302032/files/distance3_leakage.zip?download=1",
        "bytes": 426118216,
        "provider_md5_not_rehashed": "de5a595beaa3087a6e38f7c6ac3c39fb",
    },
}


class Ranges(io.RawIOBase):
    def __init__(self, url, size, budget):
        self.url, self.size, self.pos, self.budget = url, size, 0, budget
        self.responses = []
        self.bytes_read = 0
        self.cache = []

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=os.SEEK_SET):
        base = {os.SEEK_SET: 0, os.SEEK_CUR: self.pos, os.SEEK_END: self.size}[whence]
        pos = base + offset
        if pos < 0:
            raise ValueError("seek outside the archive")
        self.pos = pos
        return self.pos

    def read(self, size=-1):
        lo = self.pos
        n = min(self.size - lo, self.size if size < 0 else size)
        if n <= 0:
            return b""
        for start, cached in self.cache:
            if start <= lo and lo+n <= start+len(cached):
                self.pos += n
                return cached[lo-start:lo-start+n]
        if self.bytes_read + n > self.budget:
            raise ValueError("refuse to exceed the fixed range-read budget")
        start = lo
        size = n
        if n < 2**16:
            start = max(0, lo-2**15)
            size = min(self.size-start, max(lo+n-start, 2**16))
            if self.bytes_read + size > self.budget:
                start, size = lo, n
        hi = start+size-1
        # Use curl's system TLS trust and require a partial response, never a
        # fallback to downloading the entire file. The trailer is curl metadata.
        marker = b"\n__QEC_RANGE__"
        expected_range = f"bytes {start}-{hi}/{self.size}"
        result = subprocess.run(["curl", "-fLsS", "--max-time", "18", "--max-filesize", str(size),
                                 "-H", "Accept-Encoding: identity", "--range", f"{start}-{hi}",
                                 "--write-out", marker.decode() + "%{http_code} %header{content-range}",
                                 self.url], check=True, stdout=subprocess.PIPE)
        data, sep, trailer = result.stdout.rpartition(marker)
        if not sep or trailer.decode() != "206 " + expected_range or len(data) != size:
            raise ValueError("provider did not return the requested public byte range")
        self.responses.append({"range": expected_range, "sha256": hashlib.sha256(data).hexdigest()})
        self.pos += n
        self.bytes_read += size
        self.cache.append((start, data))
        return data[lo-start:lo-start+n]


def inventory(index, source, selected):
    entries = index.infolist()
    ext = Counter(PurePosixPath(x.filename).suffix.lower() or "(none)" for x in entries
                  if not x.is_dir())
    parts = Counter(x.filename.split("/", 1)[0] for x in entries)
    return {
        "schema": "b7_public_qec_zip_inventory_v1", "source": source,
        "entries_with_directories": len(entries), "file_extensions": dict(sorted(ext.items())),
        "top_level_entries": dict(sorted(parts.items())),
        "inventory_sha256": hashlib.sha256(json.dumps(
            [(x.filename, x.CRC, x.file_size, x.compress_size) for x in entries],
            ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
        "selected_members": selected,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", choices=ARCHIVES, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--budget-mib", type=int, default=6)
    p.add_argument("--list", help="Print only up to 36 names matching this regex")
    p.add_argument("--member", action="append", default=[], help="Exact small member names")
    p.add_argument("--member-dir", type=Path)
    a = p.parse_args()
    spec = ARCHIVES[a.archive]
    if a.out.exists() or not 1 <= a.budget_mib <= 64:
        raise ValueError("output must be new and the byte budget must be bounded")
    byte_limit = a.budget_mib * 2**20
    with Ranges(spec["url"], spec["bytes"], byte_limit) as reader, zipfile.ZipFile(reader) as z:
        if a.list:
            matches = [x for x in z.infolist() if not x.is_dir() and re.search(a.list, x.filename, re.I)]
            print("matching member names", len(matches), flush=True)
            for x in matches[:36]:
                print(x.filename, x.file_size, flush=True)
        selected = []
        for name in a.member:
            obj = z.getinfo(name)
            leaf = a.member_dir / PurePosixPath(name).name
            if obj.is_dir() or obj.file_size > byte_limit or leaf.exists():
                raise ValueError("selected member must be small and output must be new")
            raw = z.read(obj)  # also verifies the member CRC
            with leaf.open("xb") as f:
                f.write(raw)
            selected.append({"archive_name": name, "uncompressed_bytes": len(raw),
                             "zip_crc32": f"{obj.CRC:08x}", "sha256": hashlib.sha256(raw).hexdigest()})
        out = inventory(z, spec, selected)
        out["network"] = {"bytes_retrieved": reader.bytes_read, "verified_ranges": reader.responses}
    with a.out.open("x") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"{a.archive}: {out['entries_with_directories']} entries, {out['network']['bytes_retrieved']} bytes", flush=True)


if __name__ == "__main__":
    main()
