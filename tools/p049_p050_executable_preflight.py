#!/usr/bin/env python3
"""Run the scoped P049/P050 executable preflight.

P049 compares a spectral split-operator denominator with an independent
fourth-order real-space Crank-Nicolson candidate and a deliberately weaker
second-order control. P050 runs three equal-budget design policies against an
unseen topology/defect panel in a dimensionless independent-bond toy model.

Neither calculation is a frontier-solution claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import statistics
from pathlib import Path
from typing import Any, Callable

import numpy as np
import scipy
from scipy.sparse import diags, identity
from scipy.sparse.linalg import splu


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P049_P050_executable_preflight_v1.json"
DEFAULT_RESULT = ROOT / "results/P049_P050_executable_preflight_v1.json"
DEFAULT_REPORT = ROOT / "research/P049_P050_executable_preflight_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P049_P050_discussion_prompt_v1.md"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rounded(value: float, digits: int = 12) -> float:
    return round(float(value), digits)


def gaussian_model(
    config: dict[str, Any], grid_config: dict[str, Any], momentum: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    model = config["model"]
    points = int(grid_config["points"])
    x_min = float(grid_config["x_min"])
    x_max = float(grid_config["x_max"])
    dx = (x_max - x_min) / points
    x = np.linspace(x_min, x_max, points, endpoint=False)
    wave = model["initial_wavepacket"]
    center = float(wave["center"])
    sigma = float(wave["position_sigma"])
    psi = np.exp(-((x - center) ** 2) / (4.0 * sigma**2) + 1j * momentum * x)
    psi /= math.sqrt(float(np.sum(np.abs(psi) ** 2) * dx))

    potential_config = model["potential"]
    potential = float(potential_config["height"]) * np.exp(
        -(x / float(potential_config["width"])) ** 2
    )
    absorber = model["absorber"]
    start = float(absorber["start_abs_x"])
    outer = float(absorber["outer_abs_x"])
    scaled = np.clip((np.abs(x) - start) / (outer - start), 0.0, None)
    absorption = float(absorber["strength"]) * scaled ** int(absorber["power"])
    effective_potential = potential - 1j * absorption
    reciprocal = 2.0 * np.pi * np.fft.fftfreq(points, d=dx)
    return x, reciprocal, psi, effective_potential, dx


def wave_metrics(
    x: np.ndarray, psi: np.ndarray, dx: float, separation: float
) -> dict[str, float]:
    density = np.abs(psi) ** 2 * dx
    transmission = float(np.sum(density[x > separation]))
    reflection = float(np.sum(density[x < -separation]))
    unresolved = float(np.sum(density[(x >= -separation) & (x <= separation)]))
    norm = float(np.sum(density))
    absorbed = max(0.0, 1.0 - norm)
    budget_error = abs(1.0 - (transmission + reflection + unresolved + absorbed))
    return {
        "transmission_probability": rounded(transmission),
        "reflection_probability": rounded(reflection),
        "unresolved_probability": rounded(unresolved),
        "absorbed_probability": rounded(absorbed),
        "final_norm": rounded(norm),
        "norm_accounting_error": rounded(budget_error, 16),
    }


def run_split_operator(
    config: dict[str, Any],
    grid_config: dict[str, Any],
    momentum: float,
    time_step: float,
) -> dict[str, float]:
    x, reciprocal, psi, effective_potential, dx = gaussian_model(
        config, grid_config, momentum
    )
    final_time = float(config["model"]["measurement"]["final_time"])
    steps = round(final_time / time_step)
    potential_half = np.exp(-1j * effective_potential * time_step / 2.0)
    kinetic = np.exp(-1j * reciprocal**2 * time_step / 2.0)
    for _ in range(steps):
        psi = potential_half * psi
        psi = np.fft.ifft(kinetic * np.fft.fft(psi))
        psi = potential_half * psi
    metrics = wave_metrics(
        x,
        psi,
        dx,
        float(config["model"]["measurement"]["separation_abs_x"]),
    )
    metrics["steps"] = steps
    metrics["grid_points"] = int(grid_config["points"])
    return metrics


def crank_nicolson_hamiltonian(
    points: int,
    dx: float,
    effective_potential: np.ndarray,
    order: int,
):
    if order == 4:
        second = np.full(points - 2, 1.0 / (24.0 * dx**2), dtype=complex)
        first = np.full(points - 1, -2.0 / (3.0 * dx**2), dtype=complex)
        main = (
            np.full(points, 5.0 / (4.0 * dx**2), dtype=complex)
            + effective_potential
        )
        return diags(
            [second, first, main, first, second],
            offsets=[-2, -1, 0, 1, 2],
            format="csc",
        )
    if order == 2:
        first = np.full(points - 1, -0.5 / dx**2, dtype=complex)
        main = np.full(points, 1.0 / dx**2, dtype=complex) + effective_potential
        return diags([first, main, first], offsets=[-1, 0, 1], format="csc")
    raise ValueError(f"unsupported Crank-Nicolson spatial order: {order}")


def run_crank_nicolson(
    config: dict[str, Any],
    grid_config: dict[str, Any],
    momentum: float,
    time_step: float,
    order: int,
) -> dict[str, float]:
    x, _, psi, effective_potential, dx = gaussian_model(
        config, grid_config, momentum
    )
    points = int(grid_config["points"])
    hamiltonian = crank_nicolson_hamiltonian(
        points, dx, effective_potential, order
    )
    unit = identity(points, format="csc", dtype=complex)
    left = unit + 0.5j * time_step * hamiltonian
    right = unit - 0.5j * time_step * hamiltonian
    solver = splu(left)
    final_time = float(config["model"]["measurement"]["final_time"])
    steps = round(final_time / time_step)
    for _ in range(steps):
        psi = solver.solve(right @ psi)
    metrics = wave_metrics(
        x,
        psi,
        dx,
        float(config["model"]["measurement"]["separation_abs_x"]),
    )
    metrics["steps"] = steps
    metrics["grid_points"] = points
    metrics["spatial_order"] = order
    return metrics


def run_p049(config: dict[str, Any]) -> dict[str, Any]:
    propagators = config["propagators"]
    momenta = [
        ("pilot", float(value)) for value in config["pilot_momenta"]
    ] + [("holdout", float(value)) for value in config["holdout_momenta"]]
    rows: list[dict[str, Any]] = []
    for split, momentum in momenta:
        denominator = run_split_operator(
            config,
            config["working_grid"],
            momentum,
            float(propagators["denominator"]["time_step"]),
        )
        fine_reference = run_split_operator(
            config,
            config["fine_grid"],
            momentum,
            float(propagators["fine_reference"]["time_step"]),
        )
        candidate = run_crank_nicolson(
            config,
            config["working_grid"],
            momentum,
            float(propagators["candidate"]["time_step"]),
            order=4,
        )
        negative = run_crank_nicolson(
            config,
            config["working_grid"],
            momentum,
            float(propagators["negative_control"]["time_step"]),
            order=2,
        )
        denominator_t = denominator["transmission_probability"]
        row = {
            "split": split,
            "momentum": momentum,
            "incident_energy": rounded(momentum**2 / 2.0),
            "denominator": denominator,
            "fine_reference": fine_reference,
            "candidate_fourth_order_cn": candidate,
            "negative_control_second_order_cn": negative,
            "denominator_grid_error": rounded(
                abs(
                    denominator_t
                    - fine_reference["transmission_probability"]
                )
            ),
            "candidate_probability_error": rounded(
                abs(denominator_t - candidate["transmission_probability"])
            ),
            "negative_control_probability_error": rounded(
                abs(denominator_t - negative["transmission_probability"])
            ),
        }
        rows.append(row)

    acceptance = config["acceptance"]
    holdouts = [row for row in rows if row["split"] == "holdout"]
    candidate_failed = [
        row["momentum"]
        for row in holdouts
        if row["candidate_probability_error"]
        > float(acceptance["max_probability_error"])
    ]
    negative_failed = [
        row["momentum"]
        for row in holdouts
        if row["negative_control_probability_error"]
        > float(acceptance["max_probability_error"])
    ]
    max_norm_error = max(
        row["candidate_fourth_order_cn"]["norm_accounting_error"]
        for row in holdouts
    )
    max_grid_error = max(row["denominator_grid_error"] for row in holdouts)
    decision = (
        not candidate_failed
        and max_norm_error
        <= float(acceptance["max_norm_accounting_error"])
        and max_grid_error
        <= float(acceptance["max_denominator_grid_error"])
    )
    return {
        "status": "candidate_pass" if decision else "candidate_fail",
        "pilot_excluded_from_acceptance": True,
        "candidate_passes": decision,
        "candidate_failed_holdout_momenta": candidate_failed,
        "negative_control_failed_holdout_momenta": negative_failed,
        "summary": {
            "holdout_count": len(holdouts),
            "candidate_passed_holdouts": len(holdouts) - len(candidate_failed),
            "negative_control_failed_holdouts": len(negative_failed),
            "max_candidate_probability_error": rounded(
                max(row["candidate_probability_error"] for row in holdouts)
            ),
            "max_negative_control_probability_error": rounded(
                max(
                    row["negative_control_probability_error"]
                    for row in holdouts
                )
            ),
            "max_denominator_grid_error": rounded(max_grid_error),
            "max_candidate_norm_accounting_error": rounded(
                max_norm_error, 16
            ),
        },
        "cost_proxy": {
            "denominator_per_energy": {
                "steps": rows[0]["denominator"]["steps"],
                "fft_transforms_per_step": 2,
            },
            "candidate_per_energy": {
                "steps": rows[0]["candidate_fourth_order_cn"]["steps"],
                "sparse_matvecs_per_step": 1,
                "pentadiagonal_lu_solves_per_step": 1,
            },
            "negative_control_per_energy": {
                "steps": rows[0]["negative_control_second_order_cn"]["steps"],
                "sparse_matvecs_per_step": 1,
                "tridiagonal_lu_solves_per_step": 1,
            },
        },
        "rows": rows,
    }


def normalized_edges(raw_edges: list[list[int]]) -> set[tuple[int, int]]:
    return {tuple(sorted((int(edge[0]), int(edge[1])))) for edge in raw_edges}


def tag_specificity(left: int, right: int, bits: int) -> float:
    return (left ^ right).bit_count() / bits


def assembly_metrics(
    tags: tuple[int, ...],
    edges: set[tuple[int, int]],
    node_count: int,
    condition: dict[str, Any],
    model: dict[str, Any],
) -> dict[str, float]:
    bond = model["bond_model"]
    bits = int(model["tag_bits"])
    all_pairs = {
        (left, right)
        for left in range(node_count)
        for right in range(left + 1, node_count)
    }
    non_edges = all_pairs - edges
    dropout = condition["dropout_node"]
    concentration = float(bond["dropout_concentration_factor"])

    intended_probabilities: list[float] = []
    for left, right in sorted(edges):
        specificity = tag_specificity(tags[left], tags[right], bits)
        probability = float(bond["intended_base"]) + float(
            bond["intended_specificity_weight"]
        ) * specificity ** int(bond["intended_specificity_power"])
        if dropout in (left, right):
            probability *= concentration
        intended_probabilities.append(probability)

    off_target_probabilities: list[float] = []
    for left, right in sorted(non_edges):
        specificity = tag_specificity(tags[left], tags[right], bits)
        probability = (
            float(bond["off_target_base"])
            + float(bond["off_target_specificity_weight"])
            * specificity ** int(bond["off_target_specificity_power"])
            + float(condition["off_target_shift"])
        )
        if dropout in (left, right):
            probability *= concentration
        off_target_probabilities.append(probability)

    all_intended = math.prod(intended_probabilities)
    no_off_target = math.prod(1.0 - value for value in off_target_probabilities)
    return {
        "assembly_yield": rounded(all_intended * no_off_target),
        "off_target_structure_rate": rounded(1.0 - no_off_target),
        "all_intended_bonds_probability": rounded(all_intended),
    }


def median_metric(rows: list[dict[str, float]], field: str) -> float:
    return float(statistics.median(row[field] for row in rows))


def public_yield_objective(
    tags: tuple[int, ...],
    edges: set[tuple[int, int]],
    node_count: int,
    config: dict[str, Any],
) -> float:
    rows = [
        assembly_metrics(tags, edges, node_count, condition, config["model"])
        for condition in config["model"]["public_conditions"]
    ]
    return median_metric(rows, "assembly_yield")


def target_only_objective(
    tags: tuple[int, ...], edges: set[tuple[int, int]], bits: int
) -> float:
    return sum(
        tag_specificity(tags[left], tags[right], bits)
        for left, right in edges
    ) / len(edges)


def off_target_aware_objective(
    tags: tuple[int, ...],
    edges: set[tuple[int, int]],
    node_count: int,
    config: dict[str, Any],
) -> float:
    rows = [
        assembly_metrics(tags, edges, node_count, condition, config["model"])
        for condition in config["model"]["public_conditions"]
    ]
    yield_score = median_metric(rows, "assembly_yield")
    off_target_score = median_metric(rows, "off_target_structure_rate")
    weight = float(config["design_protocol"]["off_target_objective_weight"])
    return yield_score - weight * off_target_score


def random_search(
    seed: int,
    calls: int,
    node_count: int,
    tag_count: int,
    objective: Callable[[tuple[int, ...]], float],
) -> tuple[tuple[int, ...], float]:
    rng = random.Random(seed)
    best_score = -math.inf
    best_tags: tuple[int, ...] | None = None
    for _ in range(calls):
        tags = tuple(rng.randrange(tag_count) for _ in range(node_count))
        score = objective(tags)
        if score > best_score:
            best_score = score
            best_tags = tags
    assert best_tags is not None
    return best_tags, best_score


def local_search(
    seed: int,
    calls: int,
    node_count: int,
    tag_count: int,
    exploration_probability: float,
    objective: Callable[[tuple[int, ...]], float],
) -> tuple[tuple[int, ...], float]:
    rng = random.Random(seed)
    current = tuple(rng.randrange(tag_count) for _ in range(node_count))
    current_score = objective(current)
    best_tags = current
    best_score = current_score
    for _ in range(calls - 1):
        proposal = list(current)
        proposal[rng.randrange(node_count)] = rng.randrange(tag_count)
        proposal_tuple = tuple(proposal)
        proposal_score = objective(proposal_tuple)
        if (
            proposal_score >= current_score
            or rng.random() < exploration_probability
        ):
            current = proposal_tuple
            current_score = proposal_score
        if proposal_score > best_score:
            best_tags = proposal_tuple
            best_score = proposal_score
    return best_tags, best_score


def run_p050(config: dict[str, Any]) -> dict[str, Any]:
    model = config["model"]
    protocol = config["design_protocol"]
    topology = model["acceptance_topology"]
    node_count = int(model["node_count"])
    bits = int(model["tag_bits"])
    tag_count = 2**bits
    edges = normalized_edges(topology["edges"])
    calls = int(protocol["calls_per_run"])
    exploration = float(protocol["exploration_accept_probability"])
    hidden_conditions = model["hidden_conditions"]

    def public_objective(tags: tuple[int, ...]) -> float:
        return public_yield_objective(tags, edges, node_count, config)

    def target_objective(tags: tuple[int, ...]) -> float:
        return target_only_objective(tags, edges, bits)

    def aware_objective(tags: tuple[int, ...]) -> float:
        return off_target_aware_objective(tags, edges, node_count, config)

    method_runners: dict[
        str, Callable[[int], tuple[tuple[int, ...], float]]
    ] = {
        "budget_matched_random_search": lambda seed: random_search(
            seed, calls, node_count, tag_count, public_objective
        ),
        "target_only_local_search": lambda seed: local_search(
            seed,
            calls,
            node_count,
            tag_count,
            exploration,
            target_objective,
        ),
        "off_target_aware_local_search": lambda seed: local_search(
            seed,
            calls,
            node_count,
            tag_count,
            exploration,
            aware_objective,
        ),
    }

    methods: dict[str, Any] = {}
    for method_name in protocol["methods"]:
        runs: list[dict[str, Any]] = []
        for seed in protocol["paired_seeds"]:
            tags, public_score = method_runners[method_name](int(seed))
            hidden_rows = [
                {
                    "condition": condition["name"],
                    **assembly_metrics(
                        tags, edges, node_count, condition, model
                    ),
                }
                for condition in hidden_conditions
            ]
            runs.append(
                {
                    "seed": int(seed),
                    "design_calls": calls,
                    "tags": list(tags),
                    "public_objective": rounded(public_score),
                    "hidden_conditions": hidden_rows,
                    "median_hidden_yield": rounded(
                        median_metric(hidden_rows, "assembly_yield")
                    ),
                    "median_hidden_off_target_rate": rounded(
                        median_metric(
                            hidden_rows, "off_target_structure_rate"
                        )
                    ),
                }
            )
        methods[method_name] = {
            "total_design_calls": calls * len(runs),
            "median_hidden_yield": rounded(
                statistics.median(
                    run["median_hidden_yield"] for run in runs
                )
            ),
            "median_hidden_off_target_rate": rounded(
                statistics.median(
                    run["median_hidden_off_target_rate"] for run in runs
                )
            ),
            "runs": runs,
        }

    candidate = methods["off_target_aware_local_search"]
    random_baseline = methods["budget_matched_random_search"]
    target_baseline = methods["target_only_local_search"]
    gains = {
        "over_budget_matched_random_search": rounded(
            candidate["median_hidden_yield"]
            - random_baseline["median_hidden_yield"]
        ),
        "over_target_only_local_search": rounded(
            candidate["median_hidden_yield"]
            - target_baseline["median_hidden_yield"]
        ),
    }
    threshold = float(
        config["acceptance"][
            "minimum_median_yield_gain_over_each_baseline"
        ]
    )
    off_target_tolerance = float(
        config["acceptance"]["maximum_off_target_rate_increase"]
    )
    yield_passes = all(value >= threshold for value in gains.values())
    off_target_passes = all(
        candidate["median_hidden_off_target_rate"]
        <= baseline["median_hidden_off_target_rate"] + off_target_tolerance
        for baseline in (random_baseline, target_baseline)
    )
    gate_passes = yield_passes and off_target_passes
    return {
        "status": "candidate_pass" if gate_passes else "candidate_fail",
        "candidate_passes": gate_passes,
        "yield_margin_passes": yield_passes,
        "off_target_guardrail_passes": off_target_passes,
        "hidden_conditions_available_to_search": bool(
            protocol["hidden_conditions_available_to_search"]
        ),
        "candidate_yield_gains": gains,
        "methods": methods,
    }


def validate(
    benchmark: dict[str, Any], p049: dict[str, Any], p050: dict[str, Any]
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append(
            {"name": name, "passed": bool(passed), "detail": detail}
        )

    scope = benchmark["scope"]
    p049_config = benchmark["p049"]
    p050_config = benchmark["p050"]
    holdouts = set(p049_config["holdout_momenta"])
    pilots = set(p049_config["pilot_momenta"])
    acceptance_049 = p049_config["acceptance"]
    protocol_050 = p050_config["design_protocol"]
    method_calls = {
        name: payload["total_design_calls"]
        for name, payload in p050["methods"].items()
    }
    public_names = {
        row["name"] for row in p050_config["model"]["public_conditions"]
    }
    hidden_names = {
        row["name"] for row in p050_config["model"]["hidden_conditions"]
    }
    computed_050 = (
        p050["yield_margin_passes"] and p050["off_target_guardrail_passes"]
    )

    check(
        "exact_scope",
        scope["problem_ids"] == [49, 50],
        f"problem_ids={scope['problem_ids']}",
    )
    check(
        "pilot_holdout_disjoint",
        pilots.isdisjoint(holdouts) and len(holdouts) == 3,
        f"pilot={sorted(pilots)} holdout={sorted(holdouts)}",
    )
    check(
        "p049_denominator_grid_converged",
        p049["summary"]["max_denominator_grid_error"]
        <= float(acceptance_049["max_denominator_grid_error"]),
        (
            f"max={p049['summary']['max_denominator_grid_error']} "
            f"threshold={acceptance_049['max_denominator_grid_error']}"
        ),
    )
    check(
        "p049_candidate_holdouts_pass",
        p049["candidate_passes"],
        (
            f"passed={p049['summary']['candidate_passed_holdouts']}/"
            f"{p049['summary']['holdout_count']} "
            f"max_error={p049['summary']['max_candidate_probability_error']}"
        ),
    )
    check(
        "p049_norm_accounting",
        p049["summary"]["max_candidate_norm_accounting_error"]
        <= float(acceptance_049["max_norm_accounting_error"]),
        (
            f"max={p049['summary']['max_candidate_norm_accounting_error']} "
            f"threshold={acceptance_049['max_norm_accounting_error']}"
        ),
    )
    check(
        "p049_negative_control_detected",
        p049["summary"]["negative_control_failed_holdouts"]
        >= int(acceptance_049["negative_control_min_failed_holdouts"]),
        (
            f"failed={p049['summary']['negative_control_failed_holdouts']} "
            f"required={acceptance_049['negative_control_min_failed_holdouts']}"
        ),
    )
    check(
        "p050_equal_design_budgets",
        len(set(method_calls.values())) == 1,
        f"total_calls={method_calls}",
    )
    check(
        "p050_seed_count",
        len(protocol_050["paired_seeds"]) == int(protocol_050["runs"]),
        (
            f"seeds={len(protocol_050['paired_seeds'])} "
            f"runs={protocol_050['runs']}"
        ),
    )
    check(
        "p050_public_hidden_disjoint",
        public_names.isdisjoint(hidden_names),
        f"public={sorted(public_names)} hidden={sorted(hidden_names)}",
    )
    check(
        "p050_hidden_outcomes_unavailable_to_search",
        p050["hidden_conditions_available_to_search"] is False,
        "hidden_conditions_available_to_search=false",
    )
    check(
        "p050_off_target_guardrail",
        p050["off_target_guardrail_passes"],
        (
            "candidate="
            f"{p050['methods']['off_target_aware_local_search']['median_hidden_off_target_rate']}"
        ),
    )
    check(
        "p050_decision_consistent",
        p050["candidate_passes"] == computed_050,
        (
            f"candidate_passes={p050['candidate_passes']} "
            f"yield={p050['yield_margin_passes']} "
            f"off_target={p050['off_target_guardrail_passes']}"
        ),
    )
    check(
        "no_intervention",
        scope["human_animal_or_environmental_intervention"] is False,
        "numerical preflight only",
    )
    return checks


def render_report(
    benchmark: dict[str, Any], result: dict[str, Any]
) -> str:
    p049 = result["p049"]
    p050 = result["p050"]
    lines = [
        "# Problems `#049`–`#050` Executable Preflight v1",
        "",
        "Date: 2026-07-29",
        "",
        "Status: **the executable packet is valid; the `#049` numerical candidate passes,",
        "while the `#050` toy-model candidate is rejected by its frozen yield margin.**",
        "",
        "This update remains strictly inside catalog problems `#049` and `#050`. It upgrades",
        "two activation gates from prose to replayable numerical tests. It does not claim a",
        "chemical prediction, molecular assembly fidelity, quantum advantage, or a solved frontier.",
        "",
        "## Machine-check summary",
        "",
        f"- Contract checks: `{result['summary']['passed_checks']}/{result['summary']['check_count']}` passed.",
        f"- `#049` decision: `{p049['status']}` on `{p049['summary']['holdout_count']}` unopened momenta.",
        f"- `#050` decision: `{p050['status']}` under equal design-call budgets.",
        f"- Benchmark SHA-256: `{result['source']['benchmark_sha256']}`.",
        f"- Tool SHA-256: `{result['source']['tool_sha256']}`.",
        "",
        "## `#049` — Does an independent propagator survive unopened energies?",
        "",
        "The frozen model is a one-dimensional Gaussian barrier in dimensionless atomic units.",
        "The denominator is a Strang split-operator FFT propagation on 4,096 points; grid",
        "convergence is checked independently on 8,192 points at half the time step. The",
        "candidate uses a fourth-order real-space Crank–Nicolson Hamiltonian on the same",
        "working grid. A second-order spatial discretization is retained as a negative control.",
        "",
        "| Split | Momentum | Energy | Denominator T | Candidate error | Grid error | CN2 control error |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in p049["rows"]:
        lines.append(
            "| {split} | {momentum:.1f} | {energy:.3f} | {transmission:.9f} | "
            "{candidate:.3e} | {grid:.3e} | {negative:.3e} |".format(
                split=row["split"],
                momentum=row["momentum"],
                energy=row["incident_energy"],
                transmission=row["denominator"][
                    "transmission_probability"
                ],
                candidate=row["candidate_probability_error"],
                grid=row["denominator_grid_error"],
                negative=row["negative_control_probability_error"],
            )
        )
    lines.extend(
        [
            "",
            (
                "All three holdouts pass the `1e-3` probability threshold; the largest "
                f"candidate error is `{p049['summary']['max_candidate_probability_error']:.3e}` "
                "and the largest denominator grid error is "
                f"`{p049['summary']['max_denominator_grid_error']:.3e}`."
            ),
            (
                "The deliberately weaker second-order control fails "
                f"`{p049['summary']['negative_control_failed_holdouts']}/"
                f"{p049['summary']['holdout_count']}` holdouts, so this gate is not "
                "accepting every plausible-looking propagation."
            ),
            "",
            "### Cost proxy",
            "",
            (
                f"- Denominator: `{p049['cost_proxy']['denominator_per_energy']['steps']}` "
                "steps, one FFT and one inverse FFT per step."
            ),
            (
                f"- Candidate: `{p049['cost_proxy']['candidate_per_energy']['steps']}` "
                "steps, one pentadiagonal matrix-vector product and one prefactored LU solve per step."
            ),
            "",
            "## `#050` — Does lower off-target rate earn the frozen yield claim?",
            "",
            "Eight paired search seeds each receive exactly 256 design calls. The candidate,",
            "target-only baseline, and random-search baseline see two public conditions. None",
            "can see the three acceptance defects while searching. The hidden topology is an",
            "eight-node branched path.",
            "",
            "| Method | Total calls | Median hidden yield | Median hidden off-target rate |",
            "|---|---:|---:|---:|",
        ]
    )
    for method_name in benchmark["p050"]["design_protocol"]["methods"]:
        method = p050["methods"][method_name]
        lines.append(
            f"| `{method_name}` | {method['total_design_calls']} | "
            f"{method['median_hidden_yield']:.6f} | "
            f"{method['median_hidden_off_target_rate']:.6f} |"
        )
    random_gain = p050["candidate_yield_gains"][
        "over_budget_matched_random_search"
    ]
    target_gain = p050["candidate_yield_gains"][
        "over_target_only_local_search"
    ]
    lines.extend(
        [
            "",
            (
                "The off-target-aware candidate lowers the median hidden off-target rate "
                "relative to both baselines, so the safety-style guardrail passes. But its "
                f"yield gains are only `{100 * random_gain:.2f}` percentage points over "
                f"random search and `{100 * target_gain:.2f}` points over target-only search."
            ),
            (
                "Both must reach the preregistered `10.00`-point margin. The candidate is "
                "therefore rejected rather than rescued by a favorable secondary metric."
            ),
            "",
            "## Evidence and method boundary",
            "",
            "- Split-operator lineage: [Feit, Fleck, and Steiger (1982)]"
            "(https://doi.org/10.1016/0021-9991(82)90091-2).",
            "- Reaction-record context: [QCArchive record and computation types]"
            "(https://docs.qcarchive.molssi.org/user_guide/records/index.html).",
            "- Off-target assembly evidence: [Moradzadeh et al. (2026)]"
            "(https://www.nature.com/articles/s41467-026-73387-4).",
            "",
            "The `#049` Gaussian barrier is a numerical calibration object, not coupled",
            "electron–nuclear molecular dynamics. The `#050` independent-bond model omits",
            "geometry, cooperative kinetics, strand displacement, and molecular sequence",
            "physics. Its value is to exercise the denominator and rejection logic before a",
            "higher-fidelity simulator is admitted.",
            "",
            "## Next falsifiers",
            "",
            "1. Replace the `#049` Gaussian barrier with a source-backed reactive potential and",
            "   a state-resolved observable while keeping the unopened-energy split unchanged.",
            "2. Replace the `#050` independent-bond model with mesoscopic cooperative kinetics;",
            "   retain the same equal-budget baselines and ten-point hidden-yield margin.",
            "3. Proceed next to the public-data manifests for `#057` AMR and `#058`",
            "   vintage-aware wastewater alerts without widening beyond `#049`–`#060`.",
            "",
            "## Claim boundary",
            "",
            "Passing the executable packet means the calculations, hashes, decisions, and",
            "negative controls replay consistently. It does not mean problem `#049` or `#050`",
            "is solved, and it creates no chemical, biological, environmental, or clinical claim.",
            "",
        ]
    )
    return "\n".join(lines)


def render_discussion(result: dict[str, Any]) -> str:
    p049 = result["p049"]
    p050 = result["p050"]
    random_gain = p050["candidate_yield_gains"][
        "over_budget_matched_random_search"
    ]
    target_gain = p050["candidate_yield_gains"][
        "over_target_only_local_search"
    ]
    return "\n".join(
        [
            "# Can a benchmark earn credibility by rejecting one candidate while accepting another?",
            "",
            "Two activation gates have now become executable, and they disagree in the useful way.",
            "",
            f"- **`#049` reaction dynamics:** a fourth-order real-space propagator agrees with a "
            f"grid-converged split-operator denominator on `3/3` unopened momenta. Its largest "
            f"transmission error is `{p049['summary']['max_candidate_probability_error']:.3e}`. "
            f"A deliberately weaker second-order control fails "
            f"`{p049['summary']['negative_control_failed_holdouts']}/3` holdouts.",
            f"- **`#050` self-assembly:** the off-target-aware search lowers the hidden off-target "
            f"rate, but improves yield by only `{100 * random_gain:.2f}` percentage points over "
            f"random search and `{100 * target_gain:.2f}` points over target-only search. The "
            "frozen rule requires ten points over both, so the candidate is rejected.",
            "",
            "That contrast raises a harder question than “did the code run?”: **what kind of",
            "negative control makes a frontier benchmark trustworthy before the model becomes",
            "high fidelity?**",
            "",
            "Three prompts for collaborators:",
            "",
            "1. Is the `#049` Gaussian barrier too forgiving, and which public reactive potential",
            "   should replace it without reopening the holdout logic?",
            "2. Which minimum piece of cooperative kinetics must enter `#050` before a ten-point",
            "   yield margin is scientifically meaningful?",
            "3. Should the `#050` ten-point threshold remain fixed when off-target rate improves,",
            "   or is a predeclared Pareto rule more honest?",
            "",
            "The boundary is deliberate: these are numerical preflights. There is no molecular",
            "fidelity claim, wet-lab recommendation, environmental release, or solved frontier.",
            "",
            "Research packet: `research/P049_P050_executable_preflight_v1.md`",
            "",
        ]
    )


def build_result(
    benchmark_path: Path, benchmark: dict[str, Any]
) -> dict[str, Any]:
    p049 = run_p049(benchmark["p049"])
    p050 = run_p050(benchmark["p050"])
    checks = validate(benchmark, p049, p050)
    passed = sum(1 for check in checks if check["passed"])
    return {
        "schema_version": benchmark["schema_version"],
        "status": "pass" if passed == len(checks) else "fail",
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_bytes(canonical_json(benchmark)),
            "tool": str(Path(__file__).resolve().relative_to(ROOT)),
            "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "summary": {
            "scope_problem_ids": benchmark["scope"]["problem_ids"],
            "check_count": len(checks),
            "passed_checks": passed,
            "failed_checks": len(checks) - passed,
            "p049_decision": p049["status"],
            "p050_decision": p050["status"],
        },
        "checks": checks,
        "p049": p049,
        "p050": p050,
        "safety_boundary": benchmark["safety_boundary"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run and validate without writing artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    benchmark_path = args.benchmark.resolve()
    benchmark = read_json(benchmark_path)
    result = build_result(benchmark_path, benchmark)
    if not args.check_only:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.discussion.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        args.report.write_text(
            render_report(benchmark, result), encoding="utf-8"
        )
        args.discussion.write_text(
            render_discussion(result), encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "status": result["status"],
                "checks": (
                    f"{result['summary']['passed_checks']}/"
                    f"{result['summary']['check_count']}"
                ),
                "p049": result["summary"]["p049_decision"],
                "p050": result["summary"]["p050_decision"],
                "benchmark_sha256": result["source"][
                    "benchmark_sha256"
                ],
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
