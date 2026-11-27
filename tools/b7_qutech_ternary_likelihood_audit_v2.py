#!/usr/bin/env python3
"""Independently recount the fixed outcomes using packed integer bit operations."""

import argparse
from hashlib import sha256
import json
from math import comb, isclose
from pathlib import Path


COMPARATORS = ("binary_fit","matched_marginal","ternary_shuffled")
DECLARED_BITS = {"truth","ternary_aligned",*COMPARATORS}


def exact_upper_tail(k, n):
    term = total = comb(n,k)
    for j in range(k,n):
        term = term*(n-j)//(j+1)
        total += term
    return total/(1<<n)


def check(ok, what):
    if not ok:
        raise ValueError(what)


def audit(root):
    report = json.loads((root/"score.json").read_bytes())
    check([r["injection_level"] for r in report["rows"]] == [0,3],"unregistered cells")
    for row in report["rows"]:
        i,n = row["injection_level"],row["test_shots"]
        buf = (root/f"predictions_{i}.json").read_bytes()
        check(sha256(buf).hexdigest() == row["prediction_file_sha256"],"invalid packed outputs")
        src = json.loads(buf)
        check(n == src["shots"] == sum(row["shots_by_preparation"]) and
              src["bit_order"] == "little" and set(src["prediction_hex"]) == DECLARED_BITS,
              "changed denominator or policies")
        packed = {}
        for key,hex_ in src["prediction_hex"].items():
            data = bytes.fromhex(hex_)
            bits = int.from_bytes(data,"little")
            check(len(data) == (n+7)//8 and not (bits >> n),"invalid packed length")
            packed[key] = bits
        misses = {k:v ^ packed["truth"] for k,v in packed.items() if k != "truth"}
        totals = {k:v.bit_count() for k,v in misses.items()}
        check(totals == row["failures"],"failed shot counts changed")
        new = misses["ternary_aligned"]
        for key in COMPARATORS:
            other = misses[key]
            rescue,harm = (other & ~new).bit_count(),(new & ~other).bit_count()
            exact = exact_upper_tail(rescue,rescue+harm)
            cell = row["aligned_vs"][key]
            check((rescue,harm,harm-rescue) == (cell["rescued"],cell["harmed"],cell["change"])
                  and isclose(exact,cell["one_sided_p"],rel_tol=1e-11,abs_tol=1e-14),
                  "paired delta or binomial test changed")
        passed = all(row["aligned_vs"][x]["one_sided_p"] <= .0125 for x in COMPARATORS[:2])
        passed &= totals["ternary_aligned"] < totals["ternary_shuffled"]
        check(passed == row["passes_public_diagnostic"],"diagnostic verdict changed")
        print(f"level {i}: {n} exact decisions per policy; failures {totals}; pass {passed}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root",type=Path)
    audit(p.parse_args().root)
