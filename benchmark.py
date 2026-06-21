import csv
import time
from dataclasses import dataclass
from typing import Any

from graph_generator import generate_edpp_graph
from my_solver import edpp_heuristic_solver
from cplex_solver import solve_edge_disjoint_paths


def path_to_nodes(edge_path):
    if not edge_path:
        return []
    nodes = [edge_path[0][0]]
    for _, v in edge_path:
        nodes.append(v)
    return nodes


def cplex_result_to_dict(paths, p):
    result = {}
    for idx, edge_path in enumerate(paths, start=1):
        pair = (f"X_{idx}", f"Y_{idx}")
        result[pair] = path_to_nodes(edge_path)
    return result


def compare_with_guaranteed(paths_dict, guaranteed_paths):
    for pair, guaranteed in guaranteed_paths.items():
        if pair not in paths_dict:
            return False
        if paths_dict[pair] != guaranteed:
            return False
    return True


def compare_solver_paths(heuristic_paths, cplex_paths, p):
    for i in range(1, p + 1):
        pair = (f"X_{i}", f"Y_{i}")
        if pair not in heuristic_paths:
            return False
        if pair not in cplex_paths:
            return False
        if heuristic_paths[pair] != cplex_paths[pair]:
            return False
    return True


def path_cost(G, path):
    cost = 0
    for u, v in zip(path[:-1], path[1:]):
        cost += G[u][v]["weight"]
    return cost


def cplex_total_cost(G, path_dict):
    total = 0
    for path in path_dict.values():
        total += path_cost(G, path)
    return total


def format_float_for_excel(value, decimals=9):
    if value is None:
        return ""
    return f"{value:.{decimals}f}".replace(".", ",")


def serialize_value_for_excel(value: Any):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        return format_float_for_excel(value)
    return value


def serialize_row_for_excel(row: dict[str, Any]) -> dict[str, Any]:
    return {key: serialize_value_for_excel(value) for key, value in row.items()}


@dataclass
class BenchmarkConfig:
    p_values: range
    w_values: range
    k_values: range
    instances_per_config: int
    output_csv: str


def run_benchmark(config: BenchmarkConfig):
    rows = []
    total_instances = 0

    for p in config.p_values:
        for w in config.w_values:
            for k in config.k_values:
                if p > w:
                    continue

                max_targets_for_z = (w - 1) + p
                if k > max_targets_for_z:
                    continue
                if k > w:
                    continue

                for repetition in range(config.instances_per_config):
                    total_instances += 1
                    seed = 100000 * p + 1000 * w + 100 * k + repetition

                    print(f"[{total_instances}] p={p} w={w} k={k} seed={seed}")

                    try:
                        (
                            G,
                            X,
                            Y,
                            Z,
                            guaranteed_paths,
                            guaranteed_edges,
                        ) = generate_edpp_graph(
                            p=p,
                            w=w,
                            k=k,
                            seed=seed,
                        )
                    except Exception as e:
                        print(f"Błąd generacji grafu: {e}")
                        continue

                    # HEURYSTYKA
                    heuristic_success = False
                    heuristic_time = None
                    heuristic_cost = None
                    heuristic_paths = {}

                    try:
                        start = time.perf_counter()
                        heuristic_result = edpp_heuristic_solver(G, p)
                        heuristic_time = time.perf_counter() - start
                        heuristic_success = heuristic_result["success"]
                        if heuristic_success:
                            heuristic_cost = heuristic_result["total_cost"]
                            heuristic_paths = heuristic_result["paths"]
                    except Exception as e:
                        print(f"Błąd heurystyki: {e}")

                    # CPLEX
                    cplex_success = False
                    cplex_time = None
                    cplex_build_time = None
                    cplex_solve_time = None
                    cplex_extract_time = None
                    cplex_cost = None
                    cplex_paths = {}

                    try:
                        cplex_result = solve_edge_disjoint_paths(G, p)
                        cplex_success = cplex_result["success"]
                        cplex_build_time = cplex_result["build_time_sec"]
                        cplex_solve_time = cplex_result["solve_time_sec"]
                        cplex_extract_time = cplex_result["extract_time_sec"]
                        cplex_time = cplex_result["total_time_sec"]

                        if cplex_success:
                            cplex_paths = cplex_result_to_dict(
                                cplex_result["paths"], p
                            )
                            cplex_cost = cplex_total_cost(G, cplex_paths)
                    except Exception as e:
                        print(f"Błąd CPLEX: {e}")

                    # PORÓWNANIA
                    same_paths = False
                    heuristic_matches_guaranteed = False
                    cplex_matches_guaranteed = False

                    if heuristic_success and cplex_success:
                        same_paths = compare_solver_paths(
                            heuristic_paths,
                            cplex_paths,
                            p,
                        )

                    if heuristic_success:
                        heuristic_matches_guaranteed = compare_with_guaranteed(
                            heuristic_paths,
                            guaranteed_paths,
                        )

                    if cplex_success:
                        cplex_matches_guaranteed = compare_with_guaranteed(
                            cplex_paths,
                            guaranteed_paths,
                        )

                    rows.append(
                        {
                            "p": p,
                            "w": w,
                            "k": k,
                            "seed": seed,
                            "nodes": G.number_of_nodes(),
                            "edges": G.number_of_edges(),
                            "heuristic_success": heuristic_success,
                            "heuristic_time_sec": heuristic_time,
                            "heuristic_cost": heuristic_cost,
                            "heuristic_matches_guaranteed": heuristic_matches_guaranteed,
                            "cplex_success": cplex_success,
                            "cplex_build_time_sec": cplex_build_time,
                            "cplex_solve_time_sec": cplex_solve_time,
                            "cplex_extract_time_sec": cplex_extract_time,
                            "cplex_time_sec": cplex_time,
                            "cplex_cost": cplex_cost,
                            "cplex_matches_guaranteed": cplex_matches_guaranteed,
                            "same_paths": same_paths,
                        }
                    )

    if not rows:
        print("Brak wyników do zapisania.")
        return

    serialized_rows = [serialize_row_for_excel(row) for row in rows]

    with open(
        config.output_csv,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=serialized_rows[0].keys(),
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(serialized_rows)

    print(f"\nZapisano {len(rows)} rekordów do {config.output_csv}")