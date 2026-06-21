import random
from typing import Dict, List, Tuple
import networkx as nx


def generate_edpp_graph(
    p: int,
    w: int,
    k: int,
    seed: int | None = None,
) -> tuple[
    nx.DiGraph,
    list[str],
    list[str],
    list[str],
    dict[tuple[str, str], list[str]],
    dict[tuple[str, str], set[tuple[str, str]]],
]:
    """
    Generuje skierowany graf EDPP.

    Parametry
    ----------
    p : int
        Liczba par (X_i, Y_i).

    w : int
        Liczba wierzchołków pośrednich Z.

    k : int
        Liczba wymaganych połączeń:
        - każdy X_i ma dokładnie k wyjść do Z,
        - każdy Y_i ma co najmniej k wejść z Z,
        - każdy Z_j ma co najmniej k wyjść do innych Z.

    seed : int | None
        Ziarno generatora losowego.

    Zwraca
    -------
    (
        G,
        X_nodes,
        Y_nodes,
        Z_nodes,
        guaranteed_paths,
        guaranteed_edges
    )
    """

    if seed is not None:
        random.seed(seed)

    if p <= 0:
        raise ValueError("p musi być dodatnie.")

    if w <= 0:
        raise ValueError("w musi być dodatnie.")

    if k <= 0:
        raise ValueError("k musi być dodatnie.")

    if p > w:
        raise ValueError(
            "Parametry niespełnialne: musi zachodzić p <= w."
        )

    if k > (w - 1):
        raise ValueError(
            f"Nie można zapewnić {k} różnych połączeń Z->Z "
            f"przy w={w}."
        )

    X_nodes = [f"X_{i}" for i in range(1, p + 1)]
    Y_nodes = [f"Y_{i}" for i in range(1, p + 1)]
    Z_nodes = [f"Z_{i}" for i in range(1, w + 1)]

    G = nx.DiGraph()

    G.add_nodes_from(X_nodes)
    G.add_nodes_from(Y_nodes)
    G.add_nodes_from(Z_nodes)

    guaranteed_paths: dict[
        tuple[str, str],
        list[str]
    ] = {}

    guaranteed_edges: dict[
        tuple[str, str],
        set[tuple[str, str]]
    ] = {}

    def add_edge(u: str, v: str) -> bool:

        if u == v:
            return False

        if G.has_edge(u, v):
            return False

        G.add_edge(
            u,
            v,
            weight=random.randint(1, 8)
        )

        return True

    # ==========================================================
    # ETAP 1
    # Budowa gwarantowanych ścieżek
    # ==========================================================

    for i in range(p):

        x = X_nodes[i]
        y = Y_nodes[i]

        success = False

        for _ in range(100):

            z_count = random.randint(
                1,
                min(3, w)
            )

            path_z = random.sample(
                Z_nodes,
                z_count
            )

            full_path = [x] + path_z + [y]

            feasible = True

            for u, v in zip(
                full_path[:-1],
                full_path[1:]
            ):

                if G.has_edge(u, v):
                    feasible = False
                    break

            if not feasible:
                continue

            for u, v in zip(
                full_path[:-1],
                full_path[1:]
            ):

                add_edge(u, v)

            guaranteed_paths[(x, y)] = full_path

            guaranteed_edges[(x, y)] = set(
                zip(
                    full_path[:-1],
                    full_path[1:]
                )
            )

            success = True
            break

        if not success:
            raise RuntimeError(
                f"Nie udało się wygenerować ścieżki dla ({x}, {y})."
            )

    # ==========================================================
    # ETAP 2
    # Każdy Z ma co najmniej k wyjść do innych Z
    # ==========================================================

    for z in Z_nodes:

        current_z_targets = {
            v
            for _, v in G.out_edges(z)
            if v in Z_nodes
        }

        needed = k - len(current_z_targets)

        if needed <= 0:
            continue

        candidates = [
            other_z
            for other_z in Z_nodes
            if (
                other_z != z
                and other_z not in current_z_targets
                and not G.has_edge(z, other_z)
            )
        ]

        if len(candidates) < needed:
            raise RuntimeError(
                f"Nie można zapewnić {k} wyjść Z->Z dla {z}."
            )

        selected = random.sample(
            candidates,
            needed
        )

        for target in selected:

            add_edge(
                z,
                target
            )

    # ==========================================================
    # ETAP 3
    # Każdy X ma dokładnie k wyjść do Z
    # ==========================================================

    if k > w:
        raise ValueError(
            "Nie można zapewnić każdemu X "
            "dokładnie k różnych wyjść do Z."
        )

    for x in X_nodes:

        current_targets = {
            v
            for _, v in G.out_edges(x)
            if v in Z_nodes
        }

        needed = k - len(current_targets)

        if needed < 0:
            raise RuntimeError(
                f"{x} posiada więcej niż {k} wyjść."
            )

        if needed == 0:
            continue

        candidates = [
            z
            for z in Z_nodes
            if z not in current_targets
        ]

        if len(candidates) < needed:
            raise RuntimeError(
                f"Nie można uzupełnić wyjść dla {x}."
            )

        selected = random.sample(
            candidates,
            needed
        )

        for z in selected:

            add_edge(
                x,
                z
            )

    # ==========================================================
    # ETAP 4
    # Każdy Y ma co najmniej k wejść z Z
    # ==========================================================

    for y in Y_nodes:

        current_sources = {
            u
            for u, _ in G.in_edges(y)
            if u in Z_nodes
        }

        needed = k - len(current_sources)

        if needed <= 0:
            continue

        candidates = [
            z
            for z in Z_nodes
            if (
                z not in current_sources
                and not G.has_edge(z, y)
            )
        ]

        if len(candidates) < needed:
            raise RuntimeError(
                f"Nie można zapewnić {k} wejść dla {y}."
            )

        selected = random.sample(
            candidates,
            needed
        )

        for z in selected:

            add_edge(
                z,
                y
            )

    # ==========================================================
    # WALIDACJA
    # ==========================================================

    for x in X_nodes:

        if G.out_degree(x) != k:
            raise RuntimeError(
                f"{x} ma {G.out_degree(x)} wyjść zamiast {k}."
            )

        for _, v in G.out_edges(x):

            if v not in Z_nodes:
                raise RuntimeError(
                    f"{x} posiada niedozwoloną krawędź do {v}."
                )

    for z in Z_nodes:

        z_to_z_count = sum(
            1
            for _, v in G.out_edges(z)
            if v in Z_nodes
        )

        if z_to_z_count < k:
            raise RuntimeError(
                f"{z} posiada tylko {z_to_z_count} "
                f"wyjść do Z zamiast co najmniej {k}."
            )

        for _, v in G.out_edges(z):

            if (
                v not in Z_nodes
                and v not in Y_nodes
            ):
                raise RuntimeError(
                    f"{z} posiada niedozwoloną krawędź do {v}."
                )

    for y in Y_nodes:

        incoming_from_z = sum(
            1
            for u, _ in G.in_edges(y)
            if u in Z_nodes
        )

        if incoming_from_z < k:
            raise RuntimeError(
                f"{y} ma tylko {incoming_from_z} "
                f"wejść z Z."
            )

    for i in range(p):

        x = X_nodes[i]
        y = Y_nodes[i]

        if not nx.has_path(
            G,
            x,
            y
        ):
            raise RuntimeError(
                f"Brak ścieżki pomiędzy {x} i {y}."
            )

    return (
        G,
        X_nodes,
        Y_nodes,
        Z_nodes,
        guaranteed_paths,
        guaranteed_edges,
    )
def path_cost(
    G: nx.DiGraph,
    path: list[str]
) -> int:
    return sum(
        G[u][v]["weight"]
        for u, v in zip(path[:-1], path[1:])
    )