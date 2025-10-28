from pathlib import Path
from typing import Any, Dict, List, Tuple

import json
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from scripts.common.io_utils import read_json, read_yaml, ensure_dir, write_json, write_yaml

BUILD_DIR = Path("tesa-machine/build")
GRAPHS_DIR = BUILD_DIR / "graphs"
OPERATORS_DIR = BUILD_DIR / "operators"
RESULTS_DIR = Path("tesa-machine/results") / "spectrum"

def _load_graph_serial(path: Path) -> Dict[str, Any]:
    if path.suffix.lower() == ".json":
        return read_json(path)
    elif path.suffix.lower() in (".yml", ".yaml"):
        return read_yaml(path)
    else:
        raise ValueError(f"Formato não suportado: {path}")

def _serial_to_laplacian(data: Dict[str, Any]) -> Tuple[sp.csr_matrix, np.ndarray, Dict[str, Any], List[str]]:
    # nós e índice
    nodes = [nrec["id"] for nrec in data.get("nodes", [])]
    idx = {v: i for i, v in enumerate(nodes)}
    n = len(nodes)
    # pesos
    w = np.array([float(next((nr.get("weight", 1.0) for nr in data["nodes"] if nr["id"] == v), 1.0)) for v in nodes], dtype=float)
    # arestas
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
    return L, w, meta, nodes

def _projector_mean_zero(weights: np.ndarray) -> sp.csr_matrix:
    # P = I - 1 w^T, com w normalizado para soma 1
    w = weights.astype(float)
    s = float(w.sum())
    if s <= 0:
        w = np.ones_like(w)
        s = float(w.sum())
    wn = w / s
    ones = np.ones((len(wn), 1), dtype=float)
    P_dense = np.eye(len(wn)) - ones @ wn.reshape(1, -1)
    return sp.csr_matrix(P_dense)

def _renormalize(L: sp.csr_matrix, rho: float) -> sp.csr_matrix:
    rho = float(rho) if rho is not None else 1.0
    return (rho * L).tocsr()

def _smallest_positive_eig(L: sp.csr_matrix, weights: np.ndarray, k: int = 3, tol: float = 1e-8, maxiter: int | None = None) -> Dict[str, Any]:
    # projeta para subespaço de média-zero: L_hat = P^T L P
    P = _projector_mean_zero(weights)
    # Evita densificação de P^T L P: usamos operador linear implícito
    # Definimos A x = P^T L (P x)
    n = L.shape[0]

    def matvec(x: np.ndarray) -> np.ndarray:
        x = x.reshape(-1, 1)
        y = P @ x
        z = L @ y
        r = P.T @ z
        return r.ravel()

    A = spla.LinearOperator((n, n), matvec=matvec, dtype=float)

    # Tentamos obter os k menores autovalores em módulo > 0 com eigsh
    k_eff = min(max(1, k), max(1, n - 1))
    try:
        vals, vecs = spla.eigsh(A, k=k_eff, which="SM", tol=tol, maxiter=maxiter)
        # Filtra quase-zero numérico
        vals_sorted = np.sort(np.real(vals))
        pos = [v for v in vals_sorted if v > 1e-12]
        lam1 = pos[0] if pos else float(vals_sorted[-1])
        lamk = pos[:k_eff]
        return {
            "lambda1": float(lam1),
            "lambdas": [float(v) for v in lamk],
            "k_used": int(k_eff),
            "tol": float(tol),
            "notes": "",
        }
    except Exception as e:
        return {
            "lambda1": None,
            "lambdas": [],
            "k_used": int(k_eff),
            "tol": float(tol),
            "notes": f"eigsh falhou: {e}",
        }

def _process_one(graph_path: Path) -> Dict[str, Any]:
    ser = _load_graph_serial(graph_path)
    L, w, meta, nodes = _serial_to_laplacian(ser)
    rho = float(meta.get("rho", 1.0))
    gid = meta.get("id") or graph_path.stem

    # Renormaliza
    Lhat = _renormalize(L, rho)

    # Salva operadores
    ensure_dir(OPERATORS_DIR)
    # Para simplicidade, salvamos como npz com dados esparsos em formatação scipy
    sp.save_npz(OPERATORS_DIR / f"{gid}_Lz.npz", L)
    sp.save_npz(OPERATORS_DIR / f"{gid}_Lhat.npz", Lhat)
    # Metadados
    op_meta = {
        "graph_id": gid,
        "n": int(L.shape[0]),
        "rho": rho,
        "nodes": nodes,
    }
    write_json(OPERATORS_DIR / f"{gid}_meta.json", op_meta, indent=2)

    # Espectro
    spec = _smallest_positive_eig(Lhat, w, k=3, tol=1e-8, maxiter=None)
    spec["graph_id"] = gid
    spec["n"] = int(L.shape[0])
    spec["rho"] = rho

    return spec

def compute_all() -> List[Dict[str, Any]]:
    ensure_dir(RESULTS_DIR)
    # lista de grafos
    files: List[Path] = []
    for ext in ("*.json", "*.yaml", "*.yml"):
        files.extend(sorted((GRAPHS_DIR).glob(ext)))
    files = [p for p in files if p.stem not in ("index",)]

    if not files:
        raise FileNotFoundError(f"Nenhum grafo serializado encontrado em {GRAPHS_DIR}. Execute scripts/prep/build_graphs.py.")

    results: List[Dict[str, Any]] = []
    for p in files:
        try:
            res = _process_one(p)
            results.append(res)
        except Exception as e:
            results.append({
                "graph_id": p.stem,
                "error": str(e),
            })

    # salvar CSV simples e JSON agregado
    # CSV mínimo: graph_id, n, rho, lambda1, k_used, notes
    import csv
    csv_path = RESULTS_DIR / "summary_spectrum.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        wcsv = csv.writer(f)
        wcsv.writerow(["graph_id", "n", "rho", "lambda1", "k_used", "tol", "notes"])
        for r in results:
            wcsv.writerow([
                r.get("graph_id"),
                r.get("n"),
                r.get("rho"),
                r.get("lambda1"),
                r.get("k_used"),
                r.get("tol"),
                r.get("notes", ""),
            ])

    write_json(RESULTS_DIR / "summary_spectrum.json", {"results": results}, indent=2)
    write_yaml(RESULTS_DIR / "summary_spectrum.yaml", {"results": results})
    return results

if __name__ == "__main__":
    out = compute_all()
    print(f"Espectros processados: {len(out)}. Saída em {RESULTS_DIR}")