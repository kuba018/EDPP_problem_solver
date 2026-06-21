import math
import logging
from typing import Dict, List, Tuple, Hashable, Any, Optional

import networkx as nx


Node = Hashable
Path = List[Node]
Pair = Tuple[str, str]


def configure_edpp_logger(
    logger_name: str = "edpp_solver",
    log_file: Optional[str] = "edpp_solver.log",
    level: int = logging.INFO
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        if log_file is not None:
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


def build_x_y_pairs(p: int) -> List[Pair]:
    return [(f"X_{i}", f"Y_{i}") for i in range(1, p + 1)]


def path_cost(graph: nx.DiGraph, path: Path, weight: str = "weight") -> float:
    cost = 0.0
    for u, v in zip(path[:-1], path[1:]):
        cost += graph[u][v].get(weight, 1.0)
    return cost


def remove_path_edges(graph: nx.DiGraph, path: Path) -> None:
    for u, v in zip(path[:-1], path[1:]):
        if graph.has_edge(u, v):
            graph.remove_edge(u, v)


def bellman_ford_path(
    graph: nx.DiGraph,
    source: Node,
    target: Node,
    weight: str = "weight"
) -> Tuple[float, Path]:
    if source not in graph or target not in graph:
        raise ValueError(f"Brak wierzchołka {source} lub {target} w grafie.")

    dist = {node: math.inf for node in graph.nodes()}
    prev = {node: None for node in graph.nodes()}
    dist[source] = 0.0

    nodes = list(graph.nodes())
    edges = list(graph.edges(data=True))

    for _ in range(len(nodes) - 1):
        updated = False
        for u, v, data in edges:
            w = data.get(weight, 1.0)
            if dist[u] != math.inf and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                prev[v] = u
                updated = True
        if not updated:
            break

    if dist[target] == math.inf:
        raise nx.NetworkXNoPath(f"Brak ścieżki z {source} do {target}")

    path = []
    cur = target
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()

    if not path or path[0] != source:
        raise nx.NetworkXNoPath(f"Nie udało się zrekonstruować ścieżki z {source} do {target}")

    return dist[target], path


def validate_edge_disjoint(paths: Dict[Pair, Path]) -> bool:
    used_edges = set()
    for path in paths.values():
        for edge in zip(path[:-1], path[1:]):
            if edge in used_edges:
                return False
            used_edges.add(edge)
    return True


def edpp_heuristic_solver(
    graph: nx.DiGraph,
    p: int,
    weight: str = "weight",
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    Heurystyka EDPP:
    - para i to (X_i, Y_i)
    - wyznaczamy dokładnie jedną ścieżkę dla każdej pary
    - po znalezieniu ścieżki usuwamy jej krawędzie z grafu roboczego
    - przy braku rozwiązania tworzymy logi i zwracamy status niepowodzenia
    """
    if logger is None:
        logger = logging.getLogger(
            "null_edpp_solver"
        )

        logger.addHandler(
            logging.NullHandler()
        )

    if not isinstance(graph, nx.DiGraph):
        logger.error("Przekazany obiekt nie jest nx.DiGraph.")
        raise TypeError("graph musi być instancją nx.DiGraph")

    if p <= 0:
        logger.error("Niepoprawna liczba par p=%s", p)
        raise ValueError("p musi być dodatnie")

    pairs = build_x_y_pairs(p)
    working_graph = graph.copy()

    logger.info("Start solvera EDPP dla p=%s", p)
    logger.info("Liczba węzłów: %s | liczba krawędzi: %s", graph.number_of_nodes(), graph.number_of_edges())
    logger.info("Pary terminali: %s", pairs)

    paths: Dict[Pair, Path] = {}
    costs: Dict[Pair, float] = {}
    status_per_pair: Dict[Pair, str] = {}

    for s, t in pairs:
        if s not in working_graph:
            logger.error("Brak wierzchołka źródłowego %s w grafie.", s)
            status_per_pair[(s, t)] = "missing_source"
            return {
                "success": False,
                "paths": paths,
                "costs": costs,
                "total_cost": sum(costs.values()),
                "failed_pair": (s, t),
                "status_per_pair": status_per_pair,
                "edge_disjoint": validate_edge_disjoint(paths),
            }

        if t not in working_graph:
            logger.error("Brak wierzchołka docelowego %s w grafie.", t)
            status_per_pair[(s, t)] = "missing_target"
            return {
                "success": False,
                "paths": paths,
                "costs": costs,
                "total_cost": sum(costs.values()),
                "failed_pair": (s, t),
                "status_per_pair": status_per_pair,
                "edge_disjoint": validate_edge_disjoint(paths),
            }

        logger.info("Przetwarzanie pary %s -> %s", s, t)

        try:
            cost, path = bellman_ford_path(working_graph, s, t, weight=weight)
            paths[(s, t)] = path
            costs[(s, t)] = cost
            status_per_pair[(s, t)] = "ok"

            logger.info("Znaleziono ścieżkę dla %s -> %s: %s | koszt=%.3f", s, t, path, cost)

            remove_path_edges(working_graph, path)
            logger.info(
                "Usunięto %s krawędzi z grafu roboczego po obsłużeniu pary %s -> %s",
                len(path) - 1,
                s,
                t
            )

        except nx.NetworkXNoPath:
            logger.warning(
                "Brak ścieżki dla pary %s -> %s po uwzględnieniu wcześniej zajętych krawędzi.",
                s,
                t
            )
            status_per_pair[(s, t)] = "no_path"

            return {
                "success": False,
                "paths": paths,
                "costs": costs,
                "total_cost": sum(costs.values()),
                "failed_pair": (s, t),
                "status_per_pair": status_per_pair,
                "edge_disjoint": validate_edge_disjoint(paths),
            }

    edge_disjoint = validate_edge_disjoint(paths)
    if edge_disjoint:
        logger.info("Zakończono sukcesem. Wszystkie znalezione ścieżki są krawędziowo rozłączne.")
    else:
        logger.error("Błąd logiczny: znalezione ścieżki nie są krawędziowo rozłączne.")

    logger.info("Łączny koszt rozwiązania: %.3f", sum(costs.values()))

    return {
        "success": True,
        "paths": paths,
        "costs": costs,
        "total_cost": sum(costs.values()),
        "failed_pair": None,
        "status_per_pair": status_per_pair,
        "edge_disjoint": edge_disjoint,
    }