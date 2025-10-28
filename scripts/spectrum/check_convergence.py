from pathlib import Path
from typing import Any, Dict, List

import json
import math

from scripts.common.io_utils import read_json, read_yaml, ensure_dir, write_json, write_yaml

RESULTS_DIR = Path("tesa-machine/results") / "spectrum"
REPORTS_DIR = Path("tesa-machine/reports") / "validation"

def _load_summary() -> List[Dict[str, Any]]:
    summary_path_json = RESULTS_DIR / "summary_spectrum.json"
    summary_path_yaml = RESULTS_DIR / "summary_spectrum.yaml"
    if summary_path_json.exists():
        data = read_json(summary_path_json)
    elif summary_path_yaml.exists():
        data = read_yaml(summary_path_yaml)
    else:
        raise FileNotFoundError(
            f"Resumo de espectro não encontrado em {RESULTS_DIR}. Rode scripts/spectrum/compute_spectrum.py primeiro."
        )
    return data.get("results", [])

def _heuristic_convergence_check(entry: Dict[str, Any]) -> Dict[str, Any]:
    # Heurística leve:
    # - lambda1 não-nulo e positivo
    # - se houver lista de lambdas, verificar ordem crescente e positividade
    lam1 = entry.get("lambda1", None)
    lambdas = entry.get("lambdas", [])
    notes = entry.get("notes", "") or ""
    ok = True
    reasons: List[str] = []

    if lam1 is None or not isinstance(lam1, (int, float)) or not math.isfinite(lam1):
        ok = False
        reasons.append("lambda1 ausente ou não finito")
    elif lam1 <= 0:
        ok = False
        reasons.append("lambda1 não positivo")

    if lambdas and isinstance(lambdas, list):
        try:
            lambdas_f = [float(x) for x in lambdas]
            if any(x <= 0 for x in lambdas_f):
                ok = False
                reasons.append("algum autovalor não é positivo")
            if any(lambdas_f[i] > lambdas_f[i + 1] for i in range(len(lambdas_f) - 1)):
                ok = False
                reasons.append("autovalores fora de ordem não-decrescente")
            # coerência com lambda1
            if lam1 is not None and len(lambdas_f) > 0 and abs(lam1 - lambdas_f[0]) > 1e-8:
                reasons.append("lambda1 difere do primeiro de 'lambdas' (pode ser numérico)")
        except Exception:
            reasons.append("lista de 'lambdas' inválida")

    if notes and "eigsh falhou" in notes.lower():
        ok = False
        reasons.append("falha reportada pelo solver")

    return {
        "ok": ok,
        "reasons": reasons,
    }

def check_convergence() -> Dict[str, Any]:
    ensure_dir(REPORTS_DIR)
    entries = _load_summary()
    results: List[Dict[str, Any]] = []
    n_ok = 0
    n_fail = 0

    for e in entries:
        gid = e.get("graph_id")
        chk = _heuristic_convergence_check(e)
        out = {
            "graph_id": gid,
            "ok": chk["ok"],
            "reasons": chk["reasons"],
            "lambda1": e.get("lambda1"),
            "n": e.get("n"),
            "rho": e.get("rho"),
        }
        results.append(out)
        if chk["ok"]:
            n_ok += 1
        else:
            n_fail += 1

    report = {
        "summary": {
            "total": len(entries),
            "ok": n_ok,
            "fail": n_fail,
        },
        "details": results,
    }

    write_json(REPORTS_DIR / "spectrum_convergence.json", report, indent=2)
    write_yaml(REPORTS_DIR / "spectrum_convergence.yaml", report)
    return report

if __name__ == "__main__":
    rpt = check_convergence()
    print(f"Convergência: {rpt['summary']['ok']} OK, {rpt['summary']['fail']} falhas. Relatório em {REPORTS_DIR}")