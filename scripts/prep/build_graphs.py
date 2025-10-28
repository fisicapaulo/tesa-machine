from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any

import networkx as nx
import yaml

from scripts.common.io_utils import read_yaml, ensure_dir, write_json, write_yaml

DATA_DIR = Path("tesa-machine/data")
TYPES_PATH = DATA_DIR / "types" / "En_Dn_library.yaml"
BUILD_DIR = Path("tesa-machine/build")
GRAPHS_DIR = BUILD_DIR / "graphs"


@dataclass
class GraphSpec:
    id: str
    cls: str
    n: int
    vertices: List[str]
    edges: List[Dict[str, Any]]
    weights: Dict[str, float]
    rho: float
    metadata: Dict[str, Any]


def _load_types() -> List[GraphSpec]:
    """
    Carrega os tipos E_n/D_n do YAML e normaliza em GraphSpec.
    """
    if not TYPES_PATH.exists():
        raise FileNotFoundError(f"Arquivo de tipos não encontrado: {TYPES_PATH}")

    data = read_yaml(TYPES_PATH)
    if not isinstance(data, dict) or "types" not in data:
        raise ValueError("Formato inválido em En_Dn_library.yaml: chave 'types' ausente")

    specs: List[GraphSpec] = []
    for t in data["types"]:
        try:
            spec = GraphSpec(
                id=t["id"],
                cls=t.get("class") or t.get("cls") or "",
                n=int(t["n"]),
                vertices=list(t["vertices"]),
                edges=list(t.get("edges", [])),
                weights=dict(t.get("weights", {})),
                rho=float(t.get("rho", 1.0)),
                metadata=dict(t.get("metadata", {})),
            )
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Tipo inválido em 'types': {t!r} -> {e}")
        specs.append(spec)
    return specs


def _build_nx_graph(spec: GraphSpec) -> nx.Graph:
    """
    Constrói um grafo NetworkX a partir de um GraphSpec.
    - Atributos de nó: weight (float)
    - Atributos de aresta: conductance (float)
    - Atributo de grafo: rho (float), class (str), id (str), n (int)
    """
    G = nx.Graph()
    # Nós
    for v in spec.vertices:
        w = float(spec.weights.get(v, 1.0))
        G.add_node(v, weight=w)
    # Arestas
    for e in spec.edges:
        u, v = e.get("u"), e.get("v")
        if u not in G or v not in G:
            raise ValueError(f"Aresta refere nó inexistente: {e!r}")
        c = float(e.get("conductance", 1.0))
        G.add_edge(u, v, conductance=c)
    # Atributos globais
    G.graph["rho"] = spec.rho
    G.graph["class"] = spec.cls
    G.graph["id"] = spec.id
    G.graph["n"] = spec.n
    # Verificações simples
    if len(G) != spec.n:
        raise ValueError(f"n inconsistente para {spec.id}: esperado {spec.n}, obtido {len(G)}")
    return G


def _graph_summary(G: nx.Graph) -> Dict[str, Any]:
    """
    Produz um sumário leve do grafo para inspeção/depuração.
    """
    m = G.number_of_edges()
    degrees = {v: int(d) for v, d in G.degree()}
    total_weight = float(sum(G.nodes[v].get("weight", 0.0) for v in G.nodes))
    total_conductance = float(sum(G.edges[e].get("conductance", 0.0) for e in G.edges))
    return {
        "id": G.graph.get("id"),
        "class": G.graph.get("class"),
        "n": G.graph.get("n"),
        "m": m,
        "rho": G.graph.get("rho"),
        "degrees": degrees,
        "total_weight": total_weight,
        "total_conductance": total_conductance,
    }


def build_all(save_formats: Tuple[str, ...] = ("json", "yaml")) -> List[Dict[str, Any]]:
    """
    Constrói todos os grafos definidos em En_Dn_library.yaml e salva
    em tesa-machine/build/graphs/<id>.json|yaml, além de retornar um
    índice com resumos.
    """
    specs = _load_types()
    ensure_dir(GRAPHS_DIR)

    index: List[Dict[str, Any]] = []

    for spec in specs:
        G = _build_nx_graph(spec)
        summary = _graph_summary(G)
        index.append(summary)

        # Serializações leves: nós e arestas com atributos
        serial = {
            "graph": {
                "id": G.graph.get("id"),
                "class": G.graph.get("class"),
                "n": G.graph.get("n"),
                "rho": G.graph.get("rho"),
                "metadata": spec.metadata,
            },
            "nodes": [{"id": v, **G.nodes[v]} for v in G.nodes],
            "edges": [{"u": u, "v": v, **G.edges[u, v]} for u, v in G.edges],
        }

        base = GRAPHS_DIR / spec.id
        if "json" in save_formats:
            write_json(str(base) + ".json", serial, indent=2)
        if "yaml" in save_formats:
            write_yaml(str(base) + ".yaml", serial)

    # Salva índice
    write_json(GRAPHS_DIR / "index.json", {"graphs": index}, indent=2)
    write_yaml(GRAPHS_DIR / "index.yaml", {"graphs": index})
    return index


if __name__ == "__main__":
    try:
        idx = build_all()
        print(f"Construídos {len(idx)} grafo(s). Saída em {GRAPHS_DIR}")
    except Exception as e:
        print(f"Falha ao construir grafos: {e}")
