from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import networkx as nx
import yaml

from scripts.common.io_utils import read_yaml, read_json, list_files, ensure_dir, write_json, write_yaml

BUILD_DIR = Path("tesa-machine/build")
GRAPHS_DIR = BUILD_DIR / "graphs"
DATA_DIR = Path("tesa-machine/data")
METRICS_CATALOG = DATA_DIR / "metrics" / "metrics_catalog.yaml"
RESULTS_DIR = BUILD_DIR / "metrics"


@dataclass
class MetricConfig:
    name: str
    description: str
    params: Dict[str, Any]
    assumptions: str


def _load_graphs() -> List[Tuple[str, nx.Graph, Dict[str, Any]]]:
    """
    Carrega todos os grafos previamente construídos em GRAPHS_DIR (*.json ou *.yaml).
    Retorna lista de tuplas (graph_id, nx_graph, metadata_dict).
    """
    graphs: List[Tuple[str, nx.Graph, Dict[str, Any]]] = []
    # Preferir JSON pela velocidade
    files = list_files(GRAPHS_DIR, pattern="*.json")
    if not files:
        files = list_files(GRAPHS_DIR, pattern="*.yaml")
    if not files:
        raise FileNotFoundError(f"Nenhum grafo encontrado em {GRAPHS_DIR}. Execute scripts/prep/build_graphs.py primeiro.")

    def _load_one(path: str) -> Tuple[str, nx.Graph, Dict[str, Any]]:
        if path.endswith(".json"):
            data = read_json(path)
        else:
            data = read_yaml(path)
        gmeta = data.get("graph", {})
        gid = gmeta.get("id") or Path(path).stem
        G = nx.Graph()
        # atributos globais
        G.graph.update({
            "id": gid,
            "class": gmeta.get("class"),
            "n": gmeta.get("n"),
            "rho": gmeta.get("rho"),
        })
        # nós
        for nrec in data.get("nodes", []):
            nid = nrec.get("id")
            attrs = {k: v for k, v in nrec.items() if k != "id"}
            G.add_node(nid, **attrs)
        # arestas
        for erec in data.get("edges", []):
            u, v = erec.get("u"), erec.get("v")
            attrs = {k: v_ for k, v_ in erec.items() if k not in ("u", "v")}
            G.add_edge(u, v, **attrs)
        return gid, G, gmeta

    for p in files:
        if p.endswith("index.json") or p.endswith("index.yaml"):
            continue
        gid, G, meta = _load_one(p)
        graphs.append((gid, G, meta))
    return graphs


def _load_metrics_catalog() -> List[MetricConfig]:
    """
    Carrega o catálogo de métricas do YAML.
    """
    if not METRICS_CATALOG.exists():
        raise FileNotFoundError(f"Catálogo de métricas não encontrado: {METRICS_CATALOG}")
    data = read_yaml(METRICS_CATALOG)
    metrics_raw = data.get("metrics", [])
    out: List[MetricConfig] = []
    for m in metrics_raw:
        out.append(MetricConfig(
            name=m.get("name"),
            description=m.get("description", ""),
            params=m.get("params", {}) or {},
            assumptions=m.get("assumptions", "") or "",
        ))
    return out


# Implementações de métricas de exemplo (placeholders) -------------------------

def metric_arakelov_ref(G: nx.Graph, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder para 'arakelov_ref'.
    Calcula alguns agregados simples respeitando pesos e condutâncias.
    """
    n = G.number_of_nodes()
    m = G.number_of_edges()
    total_w = float(sum(G.nodes[v].get("weight", 1.0) for v in G.nodes))
    total_c = float(sum(G.edges[e].get("conductance", 1.0) for e in G.edges))
    rho = float(G.graph.get("rho", 1.0))
    norm_C0 = float(params.get("norm_C0", 1.0))
    norm_C1 = float(params.get("norm_C1", 1.0))
    norm_C2 = float(params.get("norm_C2", 1.0))
    # Heurística simples
    score = (rho + norm_C0 + 0.5 * norm_C1 + 0.25 * norm_C2) * (total_c + 1.0) / (total_w + n)
    return {
        "n": n,
        "m": m,
        "rho": rho,
        "total_weight": total_w,
        "total_conductance": total_c,
        "score": score,
    }


def metric_green_smooth_family(G: nx.Graph, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder para 'green_smooth_family'.
    Varre epsilon_grid e retorna uma curva simples baseada em propriedades do grafo.
    """
    eps_grid = params.get("epsilon_grid", [0.01, 0.02, 0.05, 0.1])
    if not isinstance(eps_grid, list):
        eps_grid = [eps_grid]
    total_c = float(sum(G.edges[e].get("conductance", 1.0) for e in G.edges))
    total_w = float(sum(G.nodes[v].get("weight", 1.0) for v in G.nodes))
    rho = float(G.graph.get("rho", 1.0))
    kappa = (total_c + 1.0) / (total_w + 1.0)
    series = []
    for eps in eps_grid:
        try:
            e = float(eps)
        except Exception:
            continue
        value = kappa * rho / (e + 1e-9)
        series.append({"epsilon": e, "value": value})
    return {
        "rho": rho,
        "kappa": kappa,
        "series": series,
        "min_value": min((p["value"] for p in series), default=None),
        "max_value": max((p["value"] for p in series), default=None),
    }


# Registry de métricas ---------------------------------------------------------

METRIC_IMPLS = {
    "arakelov_ref": metric_arakelov_ref,
    "green_smooth_family": metric_green_smooth_family,
}


def evaluate_all(selected_metrics: List[str] = None) -> Dict[str, Any]:
    """
    Avalia todas as métricas do catálogo em todos os grafos construídos.
    selected_metrics: lista opcional de nomes de métricas a rodar.
    Retorna um dicionário com resultados e um índice.
    """
    ensure_dir(RESULTS_DIR)
    graphs = _load_graphs()
    catalog = _load_metrics_catalog()

    # Filtra métricas se necessário
    if selected_metrics:
        catalog = [m for m in catalog if m.name in set(selected_metrics)]
        if not catalog:
            raise ValueError(f"Nenhuma métrica correspondente em selected_metrics={selected_metrics}")

    results_index: List[Dict[str, Any]] = []

    for mcfg in catalog:
        impl = METRIC_IMPLS.get(mcfg.name)
        if impl is None:
            # Pula métricas sem implementação
            continue
        metric_dir = ensure_dir(RESULTS_DIR / mcfg.name)
        for gid, G, meta in graphs:
            try:
                res = impl(G, mcfg.params)
                payload = {
                    "graph_id": gid,
                    "graph_meta": {
                        "class": G.graph.get("class"),
                        "n": G.graph.get("n"),
                        "rho": G.graph.get("rho"),
                    },
                    "metric": {
                        "name": mcfg.name,
                        "description": mcfg.description,
                        "params": mcfg.params,
                        "assumptions": mcfg.assumptions,
                    },
                    "result": res,
                }
                # salva por grafo
                base = metric_dir / f"{gid}"
                write_json(str(base) + ".json", payload, indent=2)
                write_yaml(str(base) + ".yaml", payload)
                results_index.append({
                    "metric": mcfg.name,
                    "graph_id": gid,
                    "path_json": str(base) + ".json",
                    "path_yaml": str(base) + ".yaml",
                })
            except Exception as e:
                err_payload = {
                    "graph_id": gid,
                    "metric": mcfg.name,
                    "error": str(e),
                }
                write_json(metric_dir / f"{gid}.error.json", err_payload, indent=2)

    # Salva índice geral
    write_json(RESULTS_DIR / "index.json", {"results": results_index}, indent=2)
    write_yaml(RESULTS_DIR / "index.yaml", {"results": results_index})

    return {"results": results_index}


if __name__ == "__main__":
    try:
        out = evaluate_all()
        print(f"Avaliações concluídas. Resultados em {RESULTS_DIR}")
    except Exception as e:
        print(f"Falha na avaliação de métricas: {e}")