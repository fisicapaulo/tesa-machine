from pathlib import Path
from typing import Any, Dict, List, Tuple, Callable

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from scripts.common.io_utils import read_json, read_yaml, ensure_dir, write_json, write_yaml

BUILD_DIR = Path("tesa-machine/build")
GRAPHS_DIR = BUILD_DIR / "graphs"
OPERATORS_DIR = BUILD_DIR / "operators"
RESULTS_DIR = Path("tesa-machine/results") / "physics"

def _load_graph_serial(path: Path) -> Dict[str, Any]:
    if path.suffix.lower() == ".json":
        return read_json(path)
    elif path.suffix.lower() in (".yml", ".yaml"):
        return read_yaml(path)
    else:
        raise ValueError(f"Formato não suportado: {path}")

def _serial_to_laplacian_incidence(data: Dict[str, Any]) -> Tuple[sp.csr_matrix, sp.csr_matrix, Dict[str, int], Dict[str, Any]]:
    # Retorna Laplaciano L = B^T C B, incidência B, índice de nós e metadados
    nodes = [nrec["id"] for nrec in data.get("nodes", [])]
    idx = {v: i for i, v in enumerate(nodes)}
    n = len(nodes)
    edges = [(e["u"], e["v"], float(e.get("conductance", 1.0))) for e in data.get("edges", [])]
    m = len(edges)
    if m == 0 or n == 0:
        raise ValueError("Grafo vazio.")

    # Incidência orientada arbitrariamente
    row = []
    col = []
    val = []
    for eid, (u, v, c) in enumerate(edges):
        i = idx[u]
        j = idx[v]
        # linha eid
        row += [eid, eid]
        col += [i, j]
        val += [1.0, -1.0]
    B = sp.coo_matrix((val, (row, col)), shape=(m, n)).tocsr()

    # Matriz de condutâncias por aresta (diagonal)
    C = sp.diags([c for (_, _, c) in edges], offsets=0, shape=(m, m), format="csr")

    # Laplaciano L = B^T C B
    L = (B.T @ C @ B).tocsr()

    meta = data.get("graph", {})
    return L, B, idx, meta

def _fenchel_energy_quadratic(L: sp.csr_matrix, b: np.ndarray) -> float:
    # Energia de Fenchel para f(x)=1/2 x^T L x com restrição L x = b é:
    # f*(y) = 1/2 b^T L^+ b, onde y = L x e x = L^+ b (no subespaço ortogonal ao kernel)
    # Portanto energia = 1/2 b^T L^+ b
    n = L.shape[0]
    # Resolver L x = b no subespaço de média-zero via CG com condicionamento leve
    # Usamos solver em subespaço ortogonal ao kernel: projetamos b para soma zero
    ones = np.ones(n)
    b_proj = b - ones * (np.dot(ones, b) / np.dot(ones, ones))

    # Definir operador linear simétrico positivo no subespaço
    def matvec(x):
        return (L @ x)

    A = spla.LinearOperator(L.shape, matvec=matvec, dtype=float)

    x, info = spla.cg(A, b_proj, tol=1e-8, maxiter=5_000)
    if info != 0:
        # fallback: regularização leve
        eps = 1e-8
        x, info2 = spla.cg(L + eps * sp.eye(n, format="csr"), b_proj, tol=1e-8, maxiter=10_000)
        if info2 != 0:
            # última tentativa: denso (pequenos)
            try:
                Ld = L.toarray()
                # adiciona regularização para inversão numérica
                Ld = Ld + eps * np.eye(n)
                x = np.linalg.solve(Ld, b_proj)
            except Exception as e:
                raise RuntimeError(f"Falha ao resolver sistema para energia de Fenchel: {e}")

    energy = 0.5 * float(b_proj @ x)
    return energy

def _build_rhs_from_sources(idx: Dict[str, int], sources: List[Dict[str, Any]]) -> np.ndarray:
    # sources: lista de {node: str, injection: float}
    n = len(idx)
    b = np.zeros(n, dtype=float)
    for s in sources:
        node = s["node"]
        inj = float(s.get("injection", 0.0))
        if node not in idx:
            raise KeyError(f"Nó desconhecido em sources: {node}")
        b[idx[node]] += inj
    return b

def compute_fenchel_energies(config_path: str | Path | None = None) -> Dict[str, Any]:
    # Configuração opcional:
    # {
    #   "scenarios": [
    #       {"graph_id": "grid_10x10", "sources": [{"node": "n_0", "injection": 1.0}, {"node": "n_55", "injection": -1.0}]},
    #       ...
    #   ]
    # }
    ensure_dir(RESULTS_DIR)
    files: List[Path] = []
    for ext in ("*.json", "*.yaml", "*.yml"):
        files.extend(sorted((GRAPHS_DIR).glob(ext)))
    files = [p for p in files if p.stem not in ("index",)]

    graphs_cache: Dict[str, Dict[str, Any]] = {}

    def load_graph(gid: str) -> Tuple[sp.csr_matrix, sp.csr_matrix, Dict[str, int], Dict[str, Any]]:
        if gid in graphs_cache:
            g = graphs_cache[gid]
            return g["L"], g["B"], g["idx"], g["meta"]
        # procurar arquivo correspondente
        for p in files:
            data = _load_graph_serial(p)
            meta = data.get("graph", {})
            this_id = meta.get("id") or p.stem
            if this_id == gid:
                L, B, idx, meta = _serial_to_laplacian_incidence(data)
                graphs_cache[gid] = {"L": L, "B": B, "idx": idx, "meta": meta}
                return L, B, idx, meta
        raise FileNotFoundError(f"Grafo com id '{gid}' não encontrado.")

    scenarios: List[Dict[str, Any]] = []
    if config_path is not None:
        config_path = Path(config_path)
        if config_path.suffix.lower() == ".json":
            cfg = read_json(config_path)
        else:
            cfg = read_yaml(config_path)
        scenarios = cfg.get("scenarios", [])

    # Se não houver cenários, criamos cenários padrão: para cada grafo, selecionar pares de nós extremos aleatórios
    if not scenarios:
        for p in files:
            data = _load_graph_serial(p)
            L, B, idx, meta = _serial_to_laplacian_incidence(data)
            gid = meta.get("id") or p.stem
            nodes = list(idx.keys())
            if len(nodes) < 2:
                continue
            # Cenário padrão: injetar +1 no primeiro nó e -1 no último
            scenarios.append({
                "graph_id": gid,
                "sources": [
                    {"node": nodes[0], "injection": 1.0},
                    {"node": nodes[-1], "injection": -1.0},
                ]
            })

    out_dir = ensure_dir(RESULTS_DIR / "fenchel_energy")
    results: List[Dict[str, Any]] = []

    for sc in scenarios:
        gid = sc["graph_id"]
        sources = sc.get("sources", [])
        L, B, idx, meta = load_graph(gid)
        b = _build_rhs_from_sources(idx, sources)
        # checagem de balanceamento: soma deve ser zero
        total = float(np.sum(b))
        if abs(total) > 1e-10:
            # Corrigir removendo média (tornar soma zero)
            n = len(b)
            b = b - total / n

        energy = _fenchel_energy_quadratic(L, b)
        payload = {
            "graph_id": gid,
            "rho": float(meta.get("rho", 1.0)),
            "n": int(L.shape[0]),
            "sources": sources,
            "energy": float(energy),
        }
        write_json(out_dir / f"{gid}.json", payload, indent=2)
        write_yaml(out_dir / f"{gid}.yaml", payload)
        results.append(payload)

    write_json(RESULTS_DIR / "fenchel_energy_index.json", {"results": results}, indent=2)
    write_yaml(RESULTS_DIR / "fenchel_energy_index.yaml", {"results": results})
    return {"results": results}

if __name__ == "__main__":
    out = compute_fenchel_energies()
    print(f"Energias de Fenchel geradas para {len(out['results'])} cenário(s). Saída em {RESULTS_DIR}/fenchel_energy")