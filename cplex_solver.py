import time

from docplex.mp.model import Model


def extract_pairs(G, num_pairs):
    pairs = []

    for i in range(1, num_pairs + 1):
        s = f"X_{i}"
        t = f"Y_{i}"

        if s not in G.nodes:
            raise ValueError(f"Brak wierzchołka {s}")

        if t not in G.nodes:
            raise ValueError(f"Brak wierzchołka {t}")

        pairs.append((s, t))

    return pairs


def build_edge_disjoint_model(G, num_pairs):
    mdl = Model(name="edge_disjoint_paths")

    pairs = extract_pairs(G, num_pairs)
    edges = list(G.edges())
    nodes = list(G.nodes())

    x = {}
    for k, (s, t) in enumerate(pairs):
        for (u, v) in edges:
            x[k, u, v] = mdl.binary_var(name=f"x_{k}_{u}_{v}")

    mdl.minimize(
        mdl.sum(
            G[u][v]["weight"] * x[k, u, v]
            for k in range(len(pairs))
            for (u, v) in edges
        )
    )

    for k, (s, t) in enumerate(pairs):
        for node in nodes:
            inflow = mdl.sum(x[k, u, v] for (u, v) in edges if v == node)
            outflow = mdl.sum(x[k, u, v] for (u, v) in edges if u == node)

            if node == s:
                mdl.add_constraint(outflow - inflow == 1)
            elif node == t:
                mdl.add_constraint(outflow - inflow == -1)
            else:
                mdl.add_constraint(outflow - inflow == 0)

    for (u, v) in edges:
        mdl.add_constraint(
            mdl.sum(x[k, u, v] for k in range(len(pairs))) <= 1
        )

    return mdl, pairs, edges, x


def extract_solution_paths(pairs, edges, x):
    paths = []

    for k, (s, t) in enumerate(pairs):
        path = []
        current = s
        visited = {s}

        while current != t:
            found = False

            for (u, v) in edges:
                if u == current and x[k, u, v].solution_value > 0.5:
                    path.append((u, v))
                    current = v

                    if current in visited and current != t:
                        raise RuntimeError(
                            "Wykryto cykl podczas odtwarzania ścieżki CPLEX"
                        )

                    visited.add(current)
                    found = True
                    break

            if not found:
                raise RuntimeError("Nie udało się odtworzyć ścieżki")

        paths.append(path)

    return paths


def solve_edge_disjoint_paths(G, num_pairs):
    build_start = time.perf_counter()
    mdl, pairs, edges, x = build_edge_disjoint_model(G, num_pairs)
    build_time = time.perf_counter() - build_start

    solve_start = time.perf_counter()
    solution = mdl.solve(log_output=False)
    solve_time = time.perf_counter() - solve_start

    if solution is None:
        return {
            "success": False,
            "paths": [],
            "objective_value": None,
            "build_time_sec": build_time,
            "solve_time_sec": solve_time,
            "extract_time_sec": 0.0,
            "total_time_sec": build_time + solve_time,
        }

    extract_start = time.perf_counter()
    paths = extract_solution_paths(pairs, edges, x)
    extract_time = time.perf_counter() - extract_start

    return {
        "success": True,
        "paths": paths,
        "objective_value": solution.objective_value,
        "build_time_sec": build_time,
        "solve_time_sec": solve_time,
        "extract_time_sec": extract_time,
        "total_time_sec": build_time + solve_time + extract_time,
    }