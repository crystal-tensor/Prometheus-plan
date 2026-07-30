#!/usr/bin/env python3
"""Capture and validate the frozen P051 public dynamics-data roster."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import platform
import re
import shlex
import ssl
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import certifi


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P051_dynamics_roster_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P051_dynamics_roster_source_v1"
DEFAULT_RESULT = ROOT / "results/P051_dynamics_roster_v1.json"
DEFAULT_REPORT = ROOT / "research/P051_dynamics_roster_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P051_dynamics_roster_discussion_v1.md"
USER_AGENT = "Axiom-Horizon-P051-roster/1.0 (+public reproducibility audit)"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

FAMILY_PREFIXES = {
    "heteronuclear_noe": ("_heteronucl_noe.",),
    "t1": ("_t1.",),
    "t2": ("_t2.",),
    "r1": ("_r1.",),
    "r2": ("_r2.",),
    "order_parameter": ("_order_param.",),
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def fetch_bytes(url: str, attempts: int = 3, timeout: int = 45) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
            },
        )
        try:
            with urllib.request.urlopen(
                request, timeout=timeout, context=SSL_CONTEXT
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} for {url}")
                return response.read()
        except Exception as exc:  # pragma: no cover - network path
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1 + attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def write_gzip(path: Path, payload: bytes) -> None:
    path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))


def read_gzip(path: Path) -> bytes:
    return gzip.decompress(path.read_bytes())


def tokenize_loop(payload: str) -> list[str]:
    lexer = shlex.shlex(payload, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = "#"
    return list(lexer)


def parse_star_loops(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    loops = []
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
            data_lines.append(lines[index])
            index += 1
        if index < len(lines):
            index += 1
        if not tags:
            continue
        try:
            tokens = tokenize_loop("\n".join(data_lines))
        except ValueError:
            loops.append(
                {
                    "tags": tags,
                    "row_count": 0,
                    "rows": [],
                    "parse_error": True,
                }
            )
            continue
        parse_error = len(tokens) % len(tags) != 0
        rows = (
            [
                tokens[position : position + len(tags)]
                for position in range(0, len(tokens), len(tags))
                if len(tokens[position : position + len(tags)]) == len(tags)
            ]
            if not parse_error
            else []
        )
        loops.append(
            {
                "tags": tags,
                "row_count": len(rows),
                "rows": rows,
                "parse_error": parse_error,
            }
        )
    return loops


def numeric(value: str) -> bool:
    if value in {".", "?"}:
        return False
    try:
        parsed = float(value)
    except ValueError:
        return False
    return parsed == parsed and abs(parsed) != float("inf")


def observable_inventory(text: str) -> dict[str, Any]:
    inventory = {
        family: {
            "numeric_row_count": 0,
            "unique_sequence_id_count": 0,
            "loop_count": 0,
            "value_tags": [],
        }
        for family in FAMILY_PREFIXES
    }
    sequence_ids = {family: set() for family in FAMILY_PREFIXES}
    parse_errors = 0
    for loop in parse_star_loops(text):
        lower_tags = [tag.lower() for tag in loop["tags"]]
        if loop["parse_error"]:
            if any(
                tag.startswith(prefix)
                for tag in lower_tags
                for prefixes in FAMILY_PREFIXES.values()
                for prefix in prefixes
            ):
                parse_errors += 1
            continue
        for family, prefixes in FAMILY_PREFIXES.items():
            matching_indices = [
                idx
                for idx, tag in enumerate(lower_tags)
                if any(tag.startswith(prefix) for prefix in prefixes)
            ]
            if not matching_indices:
                continue
            value_indices = [
                idx
                for idx in matching_indices
                if (
                    lower_tags[idx].endswith(".val")
                    or lower_tags[idx].endswith("_val")
                )
                and not lower_tags[idx].endswith("_err")
            ]
            if not value_indices:
                continue
            sequence_indices = [
                idx
                for idx in matching_indices
                if lower_tags[idx].endswith(".seq_id")
                or lower_tags[idx].endswith("_seq_id")
            ]
            family_rows = set()
            for row_position, row in enumerate(loop["rows"]):
                if any(numeric(row[idx]) for idx in value_indices):
                    family_rows.add(row_position)
                    for seq_index in sequence_indices:
                        if row[seq_index] not in {".", "?"}:
                            sequence_ids[family].add(row[seq_index])
            if family_rows:
                inventory[family]["numeric_row_count"] += len(family_rows)
                inventory[family]["loop_count"] += 1
                inventory[family]["value_tags"].extend(
                    loop["tags"][idx] for idx in value_indices
                )
    for family in inventory:
        inventory[family]["unique_sequence_id_count"] = len(sequence_ids[family])
        inventory[family]["value_tags"] = sorted(
            set(inventory[family]["value_tags"])
        )
    return {
        "families": inventory,
        "target_loop_parse_errors": parse_errors,
    }


def qualifying_families(
    inventory: dict[str, Any], minimum_rows: int
) -> list[str]:
    return sorted(
        family
        for family, values in inventory["families"].items()
        if values["numeric_row_count"] >= minimum_rows
    )


def non_null_uniprot(entry: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(fragment["uniprot_acc"])
            for chain in entry.get("construct_chains", [])
            for fragment in chain.get("fragments", [])
            if fragment.get("uniprot_acc")
        }
    )


def bmrb_xrefs(entry: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(reference["id"])
            for reference in entry.get("description", {}).get(
                "experimental_cross_reference", []
            )
            if str(reference.get("db", "")).lower() == "bmrb"
            and reference.get("id")
        }
    )


def qualifying_ensembles(
    entry: dict[str, Any], minimum_models: int
) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "ensemble_id": str(ensemble["ensemble_id"]),
                "models": int(ensemble["models"]),
            }
            for ensemble in entry.get("ensembles", [])
            if int(ensemble.get("models", 0)) >= minimum_models
        ],
        key=lambda row: row["ensemble_id"],
    )


def archive_model_count(payload: bytes) -> tuple[int, list[str]]:
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        names = sorted(
            member.name for member in archive.getmembers() if member.isfile()
        )
        pdb_names = [name for name in names if name.lower().endswith(".pdb")]
        if len(pdb_names) != 1:
            raise ValueError(
                f"expected one PDB file in ensemble archive, saw {pdb_names}"
            )
        handle = archive.extractfile(pdb_names[0])
        if handle is None:
            raise ValueError("PDB member could not be read")
        pdb_text = handle.read().decode("utf-8", errors="strict")
    model_count = sum(
        line.startswith("MODEL") for line in pdb_text.splitlines()
    )
    if model_count == 0 and any(
        line.startswith(("ATOM  ", "HETATM")) for line in pdb_text.splitlines()
    ):
        model_count = 1
    return model_count, names


def relative_file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_path(path),
        "bytes": path.stat().st_size,
    }


def capture_sources(
    benchmark: dict[str, Any],
    source_dir: Path,
) -> dict[str, Any]:
    if source_dir.exists():
        raise FileExistsError(
            f"refusing to overwrite existing frozen source directory: {source_dir}"
        )
    ped = benchmark["sources"]["ped"]
    bmrb = benchmark["sources"]["bmrb"]
    rule = benchmark["deterministic_roster_rule"]
    query_url = ped["search_url"] + "?" + urllib.parse.urlencode(ped["query"])
    openapi_bytes = fetch_bytes(ped["openapi_url"])
    search_bytes = fetch_bytes(query_url)
    policy_bytes = fetch_bytes(bmrb["policy_url"])
    search = json.loads(search_bytes)
    result_rows = sorted(search["result"], key=lambda row: row["entry_id"])
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
    roster = []
    screened = []
    selected_uniprots: set[str] = set()
    with tempfile.TemporaryDirectory(
        prefix=".p051-source-", dir=source_dir.parent
    ) as temporary:
        temp_dir = Path(temporary)
        write_gzip(temp_dir / "ped_openapi.yaml.gz", openapi_bytes)
        write_gzip(temp_dir / "ped_relaxation_search.json.gz", search_bytes)
        write_gzip(temp_dir / "bmrb_policy.html.gz", policy_bytes)
        for entry in result_rows:
            uniprots = non_null_uniprot(entry)
            xrefs = bmrb_xrefs(entry)
            ensembles = qualifying_ensembles(entry, minimum_models)
            if len(uniprots) != 1 or len(xrefs) != 1 or not ensembles:
                continue
            bmrb_id = xrefs[0]
            bmrb_url = bmrb["entry_url_template"].format(bmrb_id=bmrb_id)
            star_bytes = fetch_bytes(bmrb_url)
            star_path = temp_dir / f"bmrb_{bmrb_id}.str.gz"
            write_gzip(star_path, star_bytes)
            inventory = observable_inventory(star_bytes.decode("utf-8"))
            families = qualifying_families(inventory, minimum_rows)
            qualifies = (
                inventory["target_loop_parse_errors"] == 0
                and len(families) >= minimum_families
            )
            screen = {
                "entry_id": str(entry["entry_id"]),
                "title": str(entry["description"]["title"]),
                "uniprot_accession": uniprots[0],
                "bmrb_id": bmrb_id,
                "bmrb_url": bmrb_url,
                "bmrb_source_file": str(star_path.name),
                "bmrb_uncompressed_bytes": len(star_bytes),
                "bmrb_uncompressed_sha256": sha256_bytes(star_bytes),
                "observable_inventory": inventory,
                "qualifying_families": families,
                "metadata_ensemble_choice": ensembles[0],
                "qualifies": qualifies,
                "selected": False,
                "duplicate_uniprot_after_earlier_selection": (
                    uniprots[0] in selected_uniprots
                ),
            }
            if qualifies and uniprots[0] not in selected_uniprots:
                entry_id = str(entry["entry_id"])
                ensemble_id = ensembles[0]["ensemble_id"]
                entry_url = ped["entry_url_template"].format(entry_id=entry_id)
                archive_url = ped["ensemble_archive_url_template"].format(
                    entry_id=entry_id, ensemble_id=ensemble_id
                )
                detail_bytes = fetch_bytes(entry_url)
                archive_bytes = fetch_bytes(archive_url)
                model_count, archive_members = archive_model_count(archive_bytes)
                detail_path = temp_dir / f"{entry_id}.json.gz"
                archive_path = (
                    temp_dir / f"{entry_id}_{ensemble_id}_ensemble.tar.gz"
                )
                write_gzip(detail_path, detail_bytes)
                archive_path.write_bytes(archive_bytes)
                screen["selected"] = True
                screen["ped_entry_url"] = entry_url
                screen["ped_entry_source_file"] = detail_path.name
                screen["ensemble_archive_url"] = archive_url
                screen["ensemble_archive_source_file"] = archive_path.name
                screen["ensemble_archive_uncompressed_sha256"] = sha256_bytes(
                    archive_bytes
                )
                screen["ensemble_archive_bytes"] = len(archive_bytes)
                screen["ensemble_archive_members"] = archive_members
                screen["ensemble_archive_model_count"] = model_count
                roster.append(
                    {
                        key: screen[key]
                        for key in (
                            "entry_id",
                            "title",
                            "uniprot_accession",
                            "bmrb_id",
                            "qualifying_families",
                            "observable_inventory",
                            "metadata_ensemble_choice",
                            "ensemble_archive_model_count",
                            "bmrb_source_file",
                            "ped_entry_source_file",
                            "ensemble_archive_source_file",
                        )
                    }
                )
                selected_uniprots.add(uniprots[0])
            screened.append(screen)
            if len(roster) == target:
                break
        temp_dir.rename(source_dir)
    source_files = sorted(
        (
            relative_file_record(path)
            for path in source_dir.iterdir()
            if path.is_file()
        ),
        key=lambda row: row["path"],
    )
    return {
        "schema_version": "p051_dynamics_roster_source_v1",
        "query_url": query_url,
        "ped_reported_count": int(search["count"]),
        "ped_returned_count": len(result_rows),
        "screened_entries": screened,
        "roster": roster,
        "source_files": source_files,
    }


def synthetic_star(row_count: int = 20) -> str:
    rows = "\n".join(
        f"{index} {index} {0.5 + index / 1000:.4f}"
        for index in range(1, row_count + 1)
    )
    return "\n".join(
        [
            "data_test",
            "save_t1",
            "loop_",
            "_T1.ID",
            "_T1.Seq_ID",
            "_T1.Val",
            rows,
            "stop_",
            "save_",
            "save_t2",
            "loop_",
            "_T2.ID",
            "_T2.Seq_ID",
            "_T2.T2_val",
            rows,
            "stop_",
            "save_",
            "",
        ]
    )


def run_controls(benchmark: dict[str, Any]) -> dict[str, Any]:
    minimum_rows = int(
        benchmark["deterministic_roster_rule"][
            "bmrb_observable_requirements"
        ]["minimum_numeric_rows_per_family"]
    )
    minimum_families = int(
        benchmark["deterministic_roster_rule"][
            "bmrb_observable_requirements"
        ]["minimum_supported_families"]
    )
    positive = observable_inventory(synthetic_star(minimum_rows))
    positive_families = qualifying_families(positive, minimum_rows)
    negative = observable_inventory(
        "data_test\nsave_metadata\n_Entry.Title 'relaxation study'\nsave_\n"
    )
    negative_families = qualifying_families(negative, minimum_rows)
    return {
        "positive_numeric_loops": {
            "qualifying_families": positive_families,
            "passed": len(positive_families) >= minimum_families,
        },
        "negative_label_only": {
            "qualifying_families": negative_families,
            "passed": not negative_families,
        },
    }


def build_result(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    source_dir: Path,
    source: dict[str, Any],
    protocol_commit: str,
) -> dict[str, Any]:
    rule = benchmark["deterministic_roster_rule"]
    ped = benchmark["sources"]["ped"]
    bmrb = benchmark["sources"]["bmrb"]
    roster = source["roster"]
    target = int(rule["target_distinct_proteins"])
    minimum_rows = int(
        rule["bmrb_observable_requirements"]["minimum_numeric_rows_per_family"]
    )
    minimum_families = int(
        rule["bmrb_observable_requirements"]["minimum_supported_families"]
    )
    minimum_models = int(
        rule["entry_metadata_requirements"]["minimum_ensemble_models"]
    )
    raw = {
        Path(item["path"]).name: ROOT / item["path"]
        for item in source["source_files"]
    }
    openapi_text = read_gzip(raw["ped_openapi.yaml.gz"]).decode("utf-8")
    policy_text = read_gzip(raw["bmrb_policy.html.gz"]).decode("utf-8")
    controls = run_controls(benchmark)
    ready = (
        len(roster) == target
        and len({row["uniprot_accession"] for row in roster}) == target
        and all(len(row["qualifying_families"]) >= minimum_families for row in roster)
        and all(
            all(
                row["observable_inventory"]["families"][family][
                    "numeric_row_count"
                ]
                >= minimum_rows
                for family in row["qualifying_families"]
            )
            for row in roster
        )
        and all(row["ensemble_archive_model_count"] >= minimum_models for row in roster)
    )
    decision = (
        benchmark["readiness_decision"]["ready_label"]
        if ready
        else benchmark["readiness_decision"]["blocked_label"]
    )
    checks = [
        check(
            "scope_is_exactly_p051",
            benchmark["scope"]["included_catalog_problem_ids"] == [51],
            "Only catalog problem #051 is included.",
        ),
        check(
            "protocol_commit_recorded",
            len(protocol_commit) == 40,
            protocol_commit,
        ),
        check(
            "ped_api_version_frozen",
            f"version: '{ped['required_api_version']}'" in openapi_text,
            ped["required_api_version"],
        ),
        check(
            "ped_license_verified",
            ped["required_license"] in openapi_text,
            ped["required_license"],
        ),
        check(
            "bmrb_public_domain_policy_verified",
            bmrb["required_policy_phrase"] in policy_text,
            bmrb["required_policy_phrase"],
        ),
        check(
            "ped_search_is_complete_one_page",
            source["ped_reported_count"] == source["ped_returned_count"]
            and source["ped_returned_count"] <= int(ped["query"]["limit"]),
            f"{source['ped_returned_count']}/{source['ped_reported_count']} rows.",
        ),
        check(
            "screening_order_is_deterministic",
            [row["entry_id"] for row in source["screened_entries"]]
            == sorted(row["entry_id"] for row in source["screened_entries"]),
            "Screened PED IDs are ascending.",
        ),
        check(
            "every_retained_source_hash_matches",
            all(
                sha256_path(ROOT / item["path"]) == item["sha256"]
                for item in source["source_files"]
            ),
            f"Verified {len(source['source_files'])} retained files.",
        ),
        check(
            "target_roster_size_reached",
            len(roster) == target,
            f"Selected {len(roster)} of {target} required proteins.",
        ),
        check(
            "roster_uniprots_are_distinct",
            len({row["uniprot_accession"] for row in roster}) == len(roster),
            str([row["uniprot_accession"] for row in roster]),
        ),
        check(
            "each_roster_row_has_one_bmrb_source",
            all(row["bmrb_id"] for row in roster),
            str([row["bmrb_id"] for row in roster]),
        ),
        check(
            "each_roster_row_has_two_dynamic_families",
            all(
                len(row["qualifying_families"]) >= minimum_families
                for row in roster
            ),
            str(
                {
                    row["entry_id"]: row["qualifying_families"]
                    for row in roster
                }
            ),
        ),
        check(
            "dynamic_families_have_minimum_numeric_rows",
            all(
                all(
                    row["observable_inventory"]["families"][family][
                        "numeric_row_count"
                    ]
                    >= minimum_rows
                    for family in row["qualifying_families"]
                )
                for row in roster
            ),
            f"Minimum is {minimum_rows} numeric rows per qualifying family.",
        ),
        check(
            "coordinate_archives_have_minimum_models",
            all(
                row["ensemble_archive_model_count"] >= minimum_models
                for row in roster
            ),
            str(
                {
                    row["entry_id"]: row["ensemble_archive_model_count"]
                    for row in roster
                }
            ),
        ),
        check(
            "candidate_and_md_denominator_not_executed",
            benchmark["readiness_decision"]["candidate_model_executed"] is False
            and benchmark["readiness_decision"][
                "short_md_denominator_executed"
            ]
            is False,
            "This packet stops at source and leakage readiness.",
        ),
        check(
            "deposited_ensemble_leakage_forbidden",
            "may not predict that observable as held-out evidence"
            in benchmark["leakage_contract"]["forbidden_use"],
            benchmark["leakage_contract"]["forbidden_use"],
        ),
        check(
            "pilot_inspection_disclosed",
            len(
                benchmark["pilot_disclosure"]["inspected_during_protocol_design"]
            )
            == 3,
            benchmark["pilot_disclosure"]["boundary"],
        ),
        check(
            "synthetic_controls_pass",
            all(item["passed"] for item in controls.values()),
            str(controls),
        ),
    ]
    passed = sum(item["passed"] for item in checks)
    return {
        "schema_version": "p051_dynamics_roster_result_v1",
        "status": "pass" if passed == len(checks) else "fail",
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "tool": str(Path(__file__).resolve().relative_to(ROOT)),
            "tool_sha256": sha256_path(Path(__file__).resolve()),
            "protocol_commit": protocol_commit,
            "source_directory": str(source_dir.relative_to(ROOT)),
            "retained_files": source["source_files"],
            "query_url": source["query_url"],
        },
        "environment": {
            "python": platform.python_version(),
            "parser": "standard-library deterministic NMR-STAR loop inventory",
        },
        "decision": decision,
        "candidate_model_executed": False,
        "short_md_denominator_executed": False,
        "ped_search": {
            "reported_count": source["ped_reported_count"],
            "returned_count": source["ped_returned_count"],
            "screened_metadata_eligible_count": len(source["screened_entries"]),
        },
        "screened_entries": source["screened_entries"],
        "roster": roster,
        "controls": controls,
        "leakage_boundary": benchmark["leakage_contract"],
        "checks": checks,
        "summary": {
            "readiness_decision": decision,
            "selected_protein_count": len(roster),
            "selected_uniprot_accessions": [
                row["uniprot_accession"] for row in roster
            ],
            "selected_ped_entries": [row["entry_id"] for row in roster],
            "selected_bmrb_entries": [row["bmrb_id"] for row in roster],
            "passed_checks": passed,
            "check_count": len(checks),
            "failed_checks": [
                item["name"] for item in checks if not item["passed"]
            ],
            "next_gate": benchmark["next_gate_if_ready"],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# P051 public protein-dynamics roster v1",
        "",
        f"**Decision:** `{result['decision']}`.",
        "",
        "## What the access gate asked",
        "",
        "Can a benchmark roster be assembled from public machine-readable sources without letting an ensemble trained on every restraint grade itself? The deterministic scan starts from the complete PED `relaxation` search, requires one UniProt accession, one BMRB cross-reference, at least two numeric dynamics-observable families, and a downloadable coordinate ensemble.",
        "",
        "## Selected roster",
        "",
        "| PED | UniProt | BMRB | Qualifying dynamic families | Coordinate models |",
        "|---|---|---|---|---:|",
    ]
    for row in result["roster"]:
        family_counts = ", ".join(
            f"{family} ({row['observable_inventory']['families'][family]['numeric_row_count']})"
            for family in row["qualifying_families"]
        )
        lines.append(
            f"| [{row['entry_id']}](https://proteinensemble.org/entries/{row['entry_id']}) "
            f"| [{row['uniprot_accession']}](https://www.uniprot.org/uniprotkb/{row['uniprot_accession']}/entry) "
            f"| [{row['bmrb_id']}](https://bmrb.io/data_library/summary/index.php?bmrbId={row['bmrb_id']}) "
            f"| {family_counts} | {row['ensemble_archive_model_count']} |"
        )
    lines.extend(
        [
            "",
            "The number in parentheses is the machine-parsed count of numeric rows in that BMRB observable family. Every screened source before the deterministic stopping point, plus selected PED metadata and coordinate archives, is retained with SHA-256 hashes.",
            "",
            "## The important leakage result",
            "",
            "A PED entry can label an experiment as `relaxation` without its linked BMRB file containing numeric relaxation loops. More importantly, a deposited PED ensemble may already have been generated or selected using those same observables. It is therefore a source-format and integrity reference only: it cannot predict an observable as held-out evidence if that observable helped construct the ensemble.",
            "",
            "Any future candidate must be regenerated from training observables only. Leave-one-protein-out evaluation must exclude every observable from the held-out UniProt accession while fitting model choices. Single-structure and short-MD denominators must share the same public inputs, forward models, and sampling ledger.",
            "",
            "## What is—and is not—ready",
            "",
            f"- Formal source/access checks: `{result['summary']['passed_checks']}/{result['summary']['check_count']}`",
            f"- PED search rows retained: `{result['ped_search']['returned_count']}`",
            f"- Metadata-eligible BMRB sources screened before stop: `{result['ped_search']['screened_metadata_eligible_count']}`",
            "- Candidate ensemble executed: `false`",
            "- Short-MD denominator executed: `false`",
            "",
            "The next gate is to freeze residue mapping, observable forward models, a genuinely independent single-structure denominator, a budget-matched short-MD denominator, and training-only observable/protein splits. This packet does not evaluate AlphaFold, a force field, an ensemble generator, or biological function.",
            "",
            "## Official sources",
            "",
            "- [PED API v5 specification](https://proteinensemble.org/assets/openapi.yaml) — programmatic entry search and downloadable coordinate assets under CC BY 4.0.",
            "- [BMRB data policy](https://bmrb.io/bmrb/data_accepted.shtml) — public-domain NMR data including relaxation and order-parameter categories.",
            "",
            "No protein-engineering, clinical, therapeutic, wet-lab, or solved-frontier claim is made.",
            "",
        ]
    )
    return "\n".join(lines)


def render_discussion(result: dict[str, Any]) -> str:
    roster = ", ".join(
        f"{row['entry_id']}/{row['uniprot_accession']}"
        for row in result["roster"]
    )
    return "\n".join(
        [
            "When does an ensemble leak the experiment it claims to predict?",
            "",
            "A protein ensemble can look impressively consistent with NMR dynamics and still provide no honest held-out test if those same observables helped generate or select it. So what is the smallest benchmark design that prevents an ensemble from grading itself?",
            "",
            f"The #051 public-data gate scanned the complete PED `relaxation` result set under a deterministic rule and retained every screened BMRB source before stopping. It selected {len(result['roster'])} distinct proteins: {roster}. Each has at least two machine-readable numeric dynamics-observable families and a downloadable coordinate ensemble.",
            "",
            "That is an access result, not a model result. A deposited PED ensemble is now explicitly restricted to source-format and integrity checks. If an observable was used to construct the ensemble, that observable is forbidden as held-out evidence. No candidate ensemble or short-MD denominator has been run.",
            "",
            "The harder design question is now concrete: should the first benchmark hold out whole observable families within every protein, whole proteins, or both—and which observable forward model is sufficiently stable that a single structure, short MD, and a learned ensemble can be charged the same computational and experimental information budget?",
            "",
            "What falsifier would you freeze first: failure on one held-out protein, less than 20% median improvement over both denominators, or loss of the gain when all observables used during ensemble construction are removed?",
            "",
            f"Reproducibility: {result['summary']['passed_checks']}/{result['summary']['check_count']} formal checks; raw public source files and SHA-256 hashes are retained. No biological-function, protein-engineering, clinical, therapeutic, wet-lab, or solved-frontier claim is made.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--protocol-commit")
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    benchmark_path = args.benchmark.resolve()
    source_dir = args.source_dir.resolve()
    benchmark = read_json(benchmark_path)
    if args.self_test:
        controls = run_controls(benchmark)
        if not all(item["passed"] for item in controls.values()):
            raise SystemExit(f"self-test failed: {controls}")
        print(pretty_json({"status": "pass", "controls": controls}), end="")
        return
    if not args.protocol_commit:
        raise SystemExit("--protocol-commit is required for a formal run")
    if args.capture:
        source = capture_sources(benchmark, source_dir)
    else:
        if not args.result.exists():
            raise SystemExit("no result exists; use --capture for the first run")
        recorded = read_json(args.result.resolve())
        source = {
            "schema_version": "p051_dynamics_roster_source_v1",
            "query_url": recorded["source"]["query_url"],
            "ped_reported_count": recorded["ped_search"]["reported_count"],
            "ped_returned_count": recorded["ped_search"]["returned_count"],
            "screened_entries": recorded["screened_entries"],
            "roster": recorded["roster"],
            "source_files": recorded["source"]["retained_files"],
        }
    result = build_result(
        benchmark_path, benchmark, source_dir, source, args.protocol_commit
    )
    report = render_report(result)
    discussion = render_discussion(result)
    if args.check_only:
        if pretty_json(result) != args.result.read_text(encoding="utf-8"):
            raise SystemExit("check-only mismatch: rebuilt result differs")
        if report != args.report.read_text(encoding="utf-8"):
            raise SystemExit("check-only mismatch: rebuilt report differs")
        if discussion != args.discussion.read_text(encoding="utf-8"):
            raise SystemExit("check-only mismatch: rebuilt discussion differs")
        print(
            pretty_json(
                {
                    "status": "pass",
                    "result_sha256": sha256_path(args.result),
                    "report_sha256": sha256_path(args.report),
                    "discussion_sha256": sha256_path(args.discussion),
                }
            ),
            end="",
        )
        return
    args.result.write_text(pretty_json(result), encoding="utf-8")
    args.report.write_text(report, encoding="utf-8")
    args.discussion.write_text(discussion, encoding="utf-8")
    print(
        pretty_json(
            {
                "status": result["status"],
                "decision": result["decision"],
                "selected_entries": result["summary"]["selected_ped_entries"],
                "result": str(args.result),
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
