from pathlib import Path
from typing import Any, Dict, List, Optional

import json
import yaml
import numpy as np
import matplotlib.pyplot as plt

from scripts.common.io_utils import read_json, read_yaml, ensure_dir

RESULTS_SPECTRUM_DIR = Path("tesa-machine/results") / "spectrum"
PLOTS_DIR = Path("tesa-machine/reports") / "plots"

def _load_spectrum_entry(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.suffix.lower() == ".json":
            return read_json(path)
        elif path.suffix.lower() in (".yml", ".yaml"):
            return read_yaml(path)
    except Exception:
        return None
    return None

def _load_all_spectra() -> List[Dict[str, Any]]:
    # Espera arquivos individuais por grafo: spectrum/<graph_id>.json|yaml
    entries: List[Dict[str, Any]] = []
    if not RESULTS_SPECTRUM_DIR.exists():
        return entries
    files = []
    files.extend(sorted(RESULTS_SPECTRUM_DIR.glob("*.json")))
    files.extend(sorted(RESULTS_SPECTRUM_DIR.glob("*.yml")))
    files.extend(sorted(RESULTS_SPECTRUM_DIR.glob("*.yaml")))
    for p in files:
        if p.stem in ("summary_spectrum",):
            continue
        data = _load_spectrum_entry(p)
        if not data:
            continue
        # Normalizar: cada arquivo deve conter {graph_id, n, rho, eigenvalues: [...], k_used, tol, notes?}
        if "eigenvalues" in data and "graph_id" in data:
            entries.append(data)
        # Caso o arquivo seja um índice com results
        elif "results" in data and isinstance(data["results"], list):
            for rec in data["results"]:
                if "eigenvalues" in rec and "graph_id" in rec:
                    entries.append(rec)
    return entries

def _plot_eigenvalues(gid: str, eigvals: List[float], out_dir: Path) -> Dict[str, Any]:
    arr = np.array(eigvals, dtype=float)
    arr_sorted = np.sort(arr)

    # Plot 1: linha dos autovalores (espectro ordenado)
    plt.figure(figsize=(7, 4))
    plt.plot(np.arange(1, len(arr_sorted) + 1), arr_sorted, marker="o", linestyle="-", linewidth=1)
    plt.xlabel("índice k")
    plt.ylabel("autovalor λ_k")
    plt.title(f"Espectro do Laplaciano — {gid}")
    plt.grid(True, alpha=0.3)
    f1 = out_dir / f"{gid}_spectrum.png"
    plt.tight_layout()
    plt.savefig(f1, dpi=150)
    plt.close()

    # Plot 2: histograma de autovalores (exclui zero se presente)
    eps = 1e-14
    arr_pos = arr_sorted[arr_sorted > eps]
    plt.figure(figsize=(7, 4))
    if len(arr_pos) > 0:
        plt.hist(arr_pos, bins=min(50, max(10, len(arr_pos) // 5)), color="#4e79a7", alpha=0.85, edgecolor="black")
    else:
        # gráfico vazio com aviso
        plt.text(0.5, 0.5, "Sem autovalores positivos informados", ha="center", va="center", transform=plt.gca().transAxes)
    plt.xlabel("autovalor λ")
    plt.ylabel("contagem")
    plt.title(f"Histograma do espectro — {gid}")
    plt.grid(True, alpha=0.3)
    f2 = out_dir / f"{gid}_spectrum_hist.png"
    plt.tight_layout()
    plt.savefig(f2, dpi=150)
    plt.close()

    # Plot 3: razão espectral local λ_{k+1}/λ_k (para k >= 1)
    ratios = None
    if len(arr_pos) >= 2:
        ratios = arr_pos[1:] / np.maximum(arr_pos[:-1], eps)
        plt.figure(figsize=(7, 4))
        plt.plot(np.arange(1, len(ratios) + 1), ratios, marker="o", linestyle="-", linewidth=1, color="#f28e2b")
        plt.xlabel("k")
        plt.ylabel("λ_{k+1} / λ_k")
        plt.title(f"Razão espectral — {gid}")
        plt.grid(True, alpha=0.3)
        f3 = out_dir / f"{gid}_spectral_ratio.png"
        plt.tight_layout()
        plt.savefig(f3, dpi=150)
        plt.close()
    else:
        f3 = None

    return {
        "graph_id": gid,
        "paths": {
            "spectrum": str(f1),
            "hist": str(f2),
            "ratio": str(f3) if f3 else None,
        },
        "stats": {
            "min": float(arr_sorted.min()) if arr.size > 0 else None,
            "max": float(arr_sorted.max()) if arr.size > 0 else None,
            "count": int(arr.size),
            "count_positive": int(arr_pos.size),
            "lambda1": float(arr_pos[0]) if arr_pos.size > 0 else None,
        }
    }

def plot_all_spectra(limit_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    ensure_dir(PLOTS_DIR)
    entries = _load_all_spectra()
    if limit_ids:
        entries = [e for e in entries if e.get("graph_id") in limit_ids]

    results: List[Dict[str, Any]] = []
    for rec in entries:
        gid = rec.get("graph_id")
        eigvals = rec.get("eigenvalues", [])
        if not eigvals:
            continue
        out_dir = ensure_dir(PLOTS_DIR / "spectrum")
        res = _plot_eigenvalues(gid, eigvals, out_dir)
        results.append(res)

    # índice
    index_path_json = PLOTS_DIR / "spectrum_plots_index.json"
    index_path_yaml = PLOTS_DIR / "spectrum_plots_index.yaml"

    with open(index_path_json, "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, indent=2, ensure_ascii=False)
    with open(index_path_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump({"results": results}, f, sort_keys=False, allow_unicode=True)

    return {"results": results}

if __name__ == "__main__":
    out = plot_all_spectra()
    print(f"Plots do espectro gerados para {len(out['results'])} grafo(s). Saída em {PLOTS_DIR}/spectrum")
