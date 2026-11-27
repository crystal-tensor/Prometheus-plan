#!/usr/bin/env python3
"""Fetch and hash the frozen 4TU challenge members without reading any outcomes."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from b7_public_qec_zip_intake_v1 import ARCHIVES, Ranges, inventory


SPEC = Path("benchmarks/B7_qutech_ternary_likelihood_v2.json")


class BoundedRanges(Ranges):
    def read(self, size=-1):
        block = 512 * 1024
        if size > block:
            return b"".join(self.read(min(block, size-i)) for i in range(0, size, block))
        uri = self.url
        for attempt in range(4):
            try:
                self.url = uri if attempt % 2 == 0 else f"{uri}?download=1"
                return super().read(size)
            except subprocess.CalledProcessError:
                if attempt == 3:
                    raise
            finally:
                self.url = uri


def record(path, data):
    with path.open("x") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-dir", type=Path, required=True)
    a = p.parse_args()
    spec = json.loads(SPEC.read_bytes())
    arch = ARCHIVES[spec["source"]["archive"]]
    e = spec["experiment"]
    witnesses = {}
    with BoundedRanges(arch["url"], arch["bytes"], 20*2**20) as src, zipfile.ZipFile(src) as z:
        base = inventory(z, arch, [])
        if base["inventory_sha256"] != spec["source"]["inventory_sha256"]:
            raise ValueError("ZIP central directory changed")
        for split in ("train", "test"):
            for level in e["injection_levels_as_named_by_provider"]:
                key = f"{split}_{level}"
                target = a.artifact_dir / split / str(level)
                target.mkdir(parents=True, exist_ok=True)
                picks = []
                for state in e["prepared_bitstrings_as_integer"]:
                    leaf = f'{e["mode"]}_round_{e["rounds"]}_leak_{level}_state_{state}.txt'
                    name = f'{spec["source"]["prefix"]}/{split}/{leaf}'
                    item = z.getinfo(name)
                    if item.is_dir() or not 0 < item.file_size <= 4*2**20:
                        raise ValueError(f"unexpected measured member {name}")
                    path = target / leaf
                    if path.exists():
                        if path.is_symlink():
                            raise ValueError("expected a regular original member")
                        # Check any retained member against source before reuse.
                        raw = z.read(item)
                        if raw != path.read_bytes():
                            raise ValueError("retained member differs")
                    else:
                        raw = z.read(item)  # verifies the archive's CRC
                        with path.open("xb") as f:
                            f.write(raw)
                    picks.append({"archive_name": name, "uncompressed_bytes": len(raw),
                                  "sha256": hashlib.sha256(raw).hexdigest(),
                                  "zip_crc32": f"{item.CRC:08x}"})
                witnesses[key] = base | {"selected_members":picks}
                proof = a.artifact_dir / f"{key}.json"
                if proof.exists():
                    if json.loads(proof.read_bytes()) != witnesses[key]:
                        raise ValueError("retained receipt differs")
                else:
                    record(proof, witnesses[key])
                print(f"{key}: {len(picks)} exact members", flush=True)
        record(a.artifact_dir/"transport.json", base | {
            "network": {"bytes_retrieved": src.bytes_read, "verified_ranges": src.responses},
            "total_members": sum(len(w["selected_members"]) for w in witnesses.values())})


if __name__ == "__main__":
    main()
