from pathlib import Path
from typing import Any, Dict, List, Tuple

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

def _serial_to_laplacian_and_index(data: Dict[str, Any]) -> Tuple[sp.csr_matrix, Dict[str, int], Dict[str, Any]]:
    nodes = [nrec["id"] for nrec in data.get("nodes", [])]
    idx = {v: i for i, v in enumerate(nodes)}
    n = len(nodes)

    L = sp.lil_matrix((n, n), dtype=float)
    for erec in data.get("edges", []):
        u, v = erec["u"], erec["v"]
        c = float(erec.get("conductance", 1.0))
        i, j = idx[u], idx[v]
        L[i, i] += c
        L[j, j] += c
        L[i, j] -= c
        L[j, i] -= c
    L = L.tocsr()
    meta = data.get("graph", {})
    return L, idx, meta

def _pseudoinverse_laplacian(L: sp.csr_matrix, tol: float = 1e-10) -> sp.csr_matrix:
    # Computes Moore-Penrose pseudoinverse of Laplacian via eigendecomposition on dense small matrices
    n = L.shape[0]
    if n <= 200:
        # Dense path for small graphs
        Ld = L.toarray()
        vals, vecs = np.linalg.eigh(Ld)
        inv_vals = np.zeros_like(vals)
        for i, lam in enumerate(vals):
            if lam > tol:
                inv_vals[i] = 1.0 / lam
            else:
                inv_vals[i] = 0.0
        Lpinv = (vecs @ np.diag(inv_vals) @ vecs.T)
        return sp.csr_matrix(Lpinv)
    else:
        # Iterative approximation: use shift to handle nullspace
        # Compute k smallest positive eigenpairs
        try:
            k = min(50, max(1, n - 1))
            vals, vecs = spla.eigsh(L, k=k, which="SM", tol=1e-8)
            # filter non-positive
            mask = vals > tol
            vals = vals[mask]
            vecs = vecs[:, mask]
            Lpinv = (vecs @ np.diag(1.0 / vals) @ vecs.T)
            return sp.csr_matrix(Lpinv)
        except Exception:
            # Fallback to dense if iterative fails (may be heavy)
            Ld = L.toarray()
            vals, vecs = np.linalg.eigh(Ld)
            inv_vals = np.zeros_like(vals)
            for i, lam in enumerate(vals):
                if lam > tol:
                    inv_vals[i] = 1.0 / lam
                else:
                    inv_vals[i] = 0.0
            Lpinv = (vecs @ np.diag(inv_vals) @ vecs.T)
            return sp.csr_matrix(Lpinv)

def _effective_resistance(Lpinv: np.ndarray | sp.spmatrix, i: int, j: int) -> float:
    # R_ij = L^+_ii + L^+_jj - 2 L^+_ij
    if sp.issparse(Lpinv):
        Lp = Lpinv.toarray()
    else:
        Lp = np.asarray(Lpinv)
    return float(Lp[i, i] + Lp[j, j] - 2.0 * Lp[i, j])

def compute_effective_resistances() -> Dict[str, Any]:
    ensure_dir(RESULTS_DIR)
    files: List[Path] = []
    for ext in ("*.json", "*.yaml", "*.yml"):
        files.extend(sorted((GRAPHS_DIR).glob(ext)))
    files = [p for p in files if p.stem not in ("index",)]

    if not files:
        raise FileNotFoundError(f"Nenhum grafo encontrado em {GRAPHS_DIR}. Execute scripts/prep/build_graphs.py.")

    results_index: List[Dict[str, Any]] = []

    for p in files:
        try:
            data = _load_graph_serial(p)
            L, idx, meta = _serial_to_laplacian_and_index(data)
            gid = meta.get("id") or p.stem
            n = L.shape[0]

            # Pseudoinversa
            Lpinv = _pseudoinverse_laplacian(L)

            # Resistências efetivas para todas as arestas do grafo (pares com condutância > 0)
            resistances: List[Dict[str, Any]] = []
            for e in data.get("edges", []):
                u, v = e["u"], e["v"]
                i, j = idx[u], idx[v]
                Rij = _effective_resistance(Lpinv, i, j)
                resistances.append({
                    "u": u,
                    "v": v,
                    "effective_resistance": Rij,
                    "conductance": float(e.get("conductance", 1.0)),
                })

            # Estatísticas simples
            values = [r["effective_resistance"] for r in resistances]
            stats = {
                "min": float(np.min(values)) if values else None,
                "max": float(np.max(values)) if values else None,
                "mean": float(np.mean(values)) if values else None,
                "median": float(np.median(values)) if values else None,
            }

            payload = {
                "graph_id": gid,
                "n": int(n),
                "rho": float(meta.get("rho", 1.0)),
                "resistances_on_edges": resistances,
                "stats": stats,
            }

            out_dir = ensure_dir(RESULTS_DIR / "effective_resistance")
            write_json(out_dir / f"{gid}.json", payload, indent=2)
            write_yaml(out_dir / f"{gid}.yaml", payload)

            results_index.append({
                "graph_id": gid,
                "path_json": str(out_dir / f"{gid}.json"),
                "path_yaml": str(out_dir / f"{gid}.yaml"),
            })

        except Exception as e:
            err_dir = ensure_dir(RESULTS_DIR / "effective_resistance")
            write_json(err_dir / f"{p.stem}.error.json", {"graph_id": p.stem, "error": str(e)}, indent=2)

    # índice geral
    write_json(RESULTS_DIR / "effective_resistance_index.json", {"results": results_index}, indent=2)
    write_yaml(RESULTS_DIR / "effective_resistance_index.yaml", {"results": results_index})
    return {"results": results_index}

if __name__ == "__main__":
    out = compute_effective_resistances()
    print(f"Resistências efetivas geradas para {len(out['results'])} grafo(s). Saída em {RESULTS_DIR}/effective_resistance")