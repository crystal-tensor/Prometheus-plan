#!/usr/bin/env python3
"""Independent audit of the P051 public dynamics-data roster."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import platform
import re
import tarfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P051_dynamics_roster_v1.json"
DEFAULT_RESULT = ROOT / "results/P051_dynamics_roster_v1.json"
DEFAULT_AUDIT = ROOT / "results/P051_dynamics_roster_audit_v1.json"

FAMILY_PATTERNS = {
    "heteronuclear_noe": re.compile(r"^_Heteronucl_NOE\.", re.I),
    "t1": re.compile(r"^_T1\.", re.I),
    "t2": re.compile(r"^_T2\.", re.I),
    "r1": re.compile(r"^_R1\.", re.I),
    "r2": re.compile(r"^_R2\.", re.I),
    "order_parameter": re.compile(r"^_Order_param\.", re.I),
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def unquote_tokens(line: str) -> list[str]:
    tokens = []
    token = ""
    quote: str | None = None
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            if char == quote:
                quote = None
            else:
                token += char
        elif char in {"'", '"'}:
            quote = char
        elif char == "#":
            break
        elif char.isspace():
            if token:
                tokens.append(token)
                token = ""
        else:
            token += char
        index += 1
    if token:
        tokens.append(token)
    return tokens


def independent_inventory(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    output = {
        family: {"numeric_row_count": 0, "unique_sequence_id_count": 0}
        for family in FAMILY_PATTERNS
    }
    sequences = {family: set() for family in FAMILY_PATTERNS}
    index = 0
    while index < len(lines):
        if lines[index].strip().lower() != "loop_":
            index += 1
            continue
        index += 1
        tags = []
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped:
                index += 1
                continue
            if not stripped.startswith("_"):
                break
            tags.append(stripped.split()[0])
            index += 1
        data_lines = []
        while index < len(lines) and lines[index].strip().lower() != "stop_":
            if lines[index].strip() and not lines[index].lstrip().startswith("#"):
                data_lines.append(lines[index])
            index += 1
        if index < len(lines):
            index += 1
        for family, pattern in FAMILY_PATTERNS.items():
            positions = [
                position for position, tag in enumerate(tags) if pattern.match(tag)
            ]
            if not positions:
                continue
            value_positions = [
                position
                for position in positions
                if (
                    tags[position].lower().endswith(".val")
                    or tags[position].lower().endswith("_val")
                )
                and not tags[position].lower().endswith("_err")
            ]
            sequence_positions = [
                position
                for position in positions
                if tags[position].lower().endswith(".seq_id")
                or tags[position].lower().endswith("_seq_id")
            ]
            if not value_positions:
                continue
            pending: list[str] = []
            for line in data_lines:
                pending.extend(unquote_tokens(line))
                while len(pending) >= len(tags):
                    row = pending[: len(tags)]
                    pending = pending[len(tags) :]
                    numeric_present = False
                    for value_position in value_positions:
                        try:
                            value = float(row[value_position])
                        except ValueError:
                            continue
                        if math.isfinite(value):
                            numeric_present = True
                    if numeric_present:
                        output[family]["numeric_row_count"] += 1
                        for sequence_position in sequence_positions:
                            value = row[sequence_position]
                            if value not in {".", "?"}:
                                sequences[family].add(value)
    for family in output:
        output[family]["unique_sequence_id_count"] = len(sequences[family])
    return output


def raw_search_metadata(entry: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    uniprots = sorted(
        {
            str(fragment["uniprot_acc"])
            for chain in entry.get("construct_chains", [])
            for fragment in chain.get("fragments", [])
            if fragment.get("uniprot_acc")
        }
    )
    xrefs = sorted(
        {
            str(reference["id"])
            for reference in entry.get("description", {}).get(
                "experimental_cross_reference", []
            )
            if str(reference.get("db", "")).lower() == "bmrb"
            and reference.get("id")
        }
    )
    ensembles = sorted(
        [
            {
                "ensemble_id": str(ensemble["ensemble_id"]),
                "models": int(ensemble["models"]),
            }
            for ensemble in entry.get("ensembles", [])
        ],
        key=lambda row: row["ensemble_id"],
    )
    return uniprots, xrefs, ensembles


def archive_count(path: Path) -> int:
    with tarfile.open(fileobj=io.BytesIO(path.read_bytes()), mode="r:gz") as archive:
        members = [
            member for member in archive.getmembers()
            if member.isfile() and member.name.lower().endswith(".pdb")
        ]
        if len(members) != 1:
            return -1
        handle = archive.extractfile(members[0])
        if handle is None:
            return -1
        text = handle.read().decode("utf-8")
    count = sum(line.startswith("MODEL") for line in text.splitlines())
    if count == 0 and any(
        line.startswith(("ATOM  ", "HETATM")) for line in text.splitlines()
    ):
        count = 1
    return count


def build_audit(
    benchmark_path: Path, result_path: Path
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    result = read_json(result_path)
    source_dir = ROOT / result["source"]["source_directory"]
    retained = result["source"]["retained_files"]
    raw_search = json.loads(
        gzip.decompress(
            (source_dir / "ped_relaxation_search.json.gz").read_bytes()
        )
    )
    raw_rows = sorted(raw_search["result"], key=lambda row: row["entry_id"])
    rule = benchmark["deterministic_roster_rule"]
    minimum_models = int(
        rule["entry_metadata_requirements"]["minimum_ensemble_models"]
    )
    minimum_rows = int(
        rule["bmrb_observable_requirements"]["minimum_numeric_rows_per_family"]
    )
    minimum_families = int(
        rule["bmrb_observable_requirements"]["minimum_supported_families"]
    )
    target = int(rule["target_distinct_proteins"])
    reconstructed_screened = []
    reconstructed_roster = []
    selected_uniprots: set[str] = set()
    for entry in raw_rows:
        uniprots, xrefs, all_ensembles = raw_search_metadata(entry)
        ensembles = [
            row for row in all_ensembles if row["models"] >= minimum_models
        ]
        if len(uniprots) != 1 or len(xrefs) != 1 or not ensembles:
            continue
        bmrb_path = source_dir / f"bmrb_{xrefs[0]}.str.gz"
        if not bmrb_path.exists():
            break
        text = gzip.decompress(bmrb_path.read_bytes()).decode("utf-8")
        inventory = independent_inventory(text)
        families = sorted(
            family
            for family, values in inventory.items()
            if values["numeric_row_count"] >= minimum_rows
        )
        qualifies = len(families) >= minimum_families
        selected = qualifies and uniprots[0] not in selected_uniprots
        reconstructed_screened.append(
            {
                "entry_id": entry["entry_id"],
                "uniprot_accession": uniprots[0],
                "bmrb_id": xrefs[0],
                "families": families,
                "selected": selected,
            }
        )
        if selected:
            ensemble = ensembles[0]
            archive_path = (
                source_dir
                / f"{entry['entry_id']}_{ensemble['ensemble_id']}_ensemble.tar.gz"
            )
            reconstructed_roster.append(
                {
                    "entry_id": entry["entry_id"],
                    "uniprot_accession": uniprots[0],
                    "bmrb_id": xrefs[0],
                    "families": families,
                    "models": archive_count(archive_path),
                }
            )
            selected_uniprots.add(uniprots[0])
        if len(reconstructed_roster) == target:
            break
    recorded_screened = [
        {
            "entry_id": row["entry_id"],
            "uniprot_accession": row["uniprot_accession"],
            "bmrb_id": row["bmrb_id"],
            "families": row["qualifying_families"],
            "selected": row["selected"],
        }
        for row in result["screened_entries"]
    ]
    recorded_roster = [
        {
            "entry_id": row["entry_id"],
            "uniprot_accession": row["uniprot_accession"],
            "bmrb_id": row["bmrb_id"],
            "families": row["qualifying_families"],
            "models": row["ensemble_archive_model_count"],
        }
        for row in result["roster"]
    ]
    family_count_differences = []
    for row in result["roster"]:
        text = gzip.decompress(
            (source_dir / row["bmrb_source_file"]).read_bytes()
        ).decode("utf-8")
        independent = independent_inventory(text)
        for family in row["qualifying_families"]:
            family_count_differences.append(
                abs(
                    independent[family]["numeric_row_count"]
                    - row["observable_inventory"]["families"][family][
                        "numeric_row_count"
                    ]
                )
            )
    checks = [
        check(
            "formal_result_passed",
            result["status"] == "pass",
            result["status"],
        ),
        check(
            "protocol_commit_recorded",
            len(result["source"]["protocol_commit"]) == 40,
            result["source"]["protocol_commit"],
        ),
        check(
            "all_retained_file_hashes_match",
            all(
                sha256_path(ROOT / item["path"]) == item["sha256"]
                for item in retained
            ),
            f"Verified {len(retained)} files.",
        ),
        check(
            "raw_search_count_matches",
            int(raw_search["count"]) == len(raw_rows)
            == result["ped_search"]["returned_count"],
            f"Observed {len(raw_rows)} rows.",
        ),
        check(
            "independent_screening_order_and_selection_match",
            reconstructed_screened == recorded_screened,
            f"Rebuilt {len(reconstructed_screened)} screened entries.",
        ),
        check(
            "independent_roster_matches",
            reconstructed_roster == recorded_roster,
            str(reconstructed_roster),
        ),
        check(
            "independent_observable_counts_match",
            max(family_count_differences, default=math.inf) == 0,
            f"Maximum row-count difference {max(family_count_differences, default=math.inf)}.",
        ),
        check(
            "independent_readiness_decision_matches",
            result["decision"]
            == (
                benchmark["readiness_decision"]["ready_label"]
                if len(reconstructed_roster) == target
                and len(
                    {
                        row["uniprot_accession"]
                        for row in reconstructed_roster
                    }
                )
                == target
                else benchmark["readiness_decision"]["blocked_label"]
            ),
            (
                f"Recovered {len(reconstructed_roster)} of {target}; "
                f"decision is {result['decision']}."
            ),
        ),
        check(
            "coordinate_archive_counts_match",
            all(row["models"] >= minimum_models for row in reconstructed_roster),
            str(
                {
                    row["entry_id"]: row["models"]
                    for row in reconstructed_roster
                }
            ),
        ),
        check(
            "candidate_execution_remains_false",
            result["candidate_model_executed"] is False
            and result["short_md_denominator_executed"] is False,
            "The audit covers access and leakage only.",
        ),
    ]
    passed = sum(row["passed"] for row in checks)
    return {
        "schema_version": "p051_dynamics_roster_audit_v1",
        "status": "pass" if passed == len(checks) else "fail",
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "formal_result": str(result_path.relative_to(ROOT)),
            "formal_result_sha256": sha256_path(result_path),
            "audit_tool": str(Path(__file__).resolve().relative_to(ROOT)),
            "audit_tool_sha256": sha256_path(Path(__file__).resolve()),
            "protocol_commit": result["source"]["protocol_commit"],
        },
        "environment": {
            "python": platform.python_version(),
            "parser": "independent line-state NMR-STAR inventory",
        },
        "independent_roster": reconstructed_roster,
        "maximum_observable_row_count_difference": max(
            family_count_differences, default=math.inf
        ),
        "checks": checks,
        "summary": {
            "passed_checks": passed,
            "check_count": len(checks),
            "failed_checks": [
                row["name"] for row in checks if not row["passed"]
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = build_audit(args.benchmark.resolve(), args.result.resolve())
    if args.check_only:
        recorded = read_json(args.audit.resolve())
        if pretty_json(audit) != pretty_json(recorded):
            raise SystemExit("check-only mismatch: rebuilt audit differs")
        print(
            pretty_json(
                {"status": "pass", "audit_sha256": sha256_path(args.audit)}
            ),
            end="",
        )
        return
    args.audit.write_text(pretty_json(audit), encoding="utf-8")
    print(
        pretty_json(
            {
                "status": audit["status"],
                "audit": str(args.audit),
                "checks": audit["summary"],
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
