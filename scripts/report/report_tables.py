from pathlib import Path
from typing import Any, Dict, List

import csv

from scripts.common.io_utils import read_json, read_yaml, ensure_dir, write_json, write_yaml

RESULTS_SPECTRUM_DIR = Path("tesa-machine/results") / "spectrum"
RESULTS_PHYSICS_DIR = Path("tesa-machine/results") / "physics"
REPORTS_DIR = Path("tesa-machine/reports") / "tables"

def _load_spectrum_summary() -> List[Dict[str, Any]]:
    pjson = RESULTS_SPECTRUM_DIR / "summary_spectrum.json"
    pyaml = RESULTS_SPECTRUM_DIR / "summary_spectrum.yaml"
    if pjson.exists():
        data = read_json(pjson)
    elif pyaml.exists():
        data = read_yaml(pyaml)
    else:
        return []
    return data.get("results", [])

def _load_effective_resistance_index() -> List[Dict[str, Any]]:
    pjson = RESULTS_PHYSICS_DIR / "effective_resistance_index.json"
    pyaml = RESULTS_PHYSICS_DIR / "effective_resistance_index.yaml"
    if pjson.exists():
        data = read_json(pjson)
    elif pyaml.exists():
        data = read_yaml(pyaml)
    else:
        return []
    return data.get("results", [])

def _load_fenchel_energy_index() -> List[Dict[str, Any]]:
    pjson = RESULTS_PHYSICS_DIR / "fenchel_energy_index.json"
    pyaml = RESULTS_PHYSICS_DIR / "fenchel_energy_index.yaml"
    if pjson.exists():
        data = read_json(pjson)
    elif pyaml.exists():
        data = read_yaml(pyaml)
    else:
        return []
    return data.get("results", [])

def _collect_effective_resistance_stats() -> List[Dict[str, Any]]:
    index = _load_effective_resistance_index()
    out: List[Dict[str, Any]] = []
    for entry in index:
        p = Path(entry.get("path_json", ""))
        if not p.exists():
            continue
        data = read_json(p)
        stats = data.get("stats", {})
        out.append({
            "graph_id": data.get("graph_id"),
            "n": data.get("n"),
            "rho": data.get("rho"),
            "effective_resistance_min": stats.get("min"),
            "effective_resistance_max": stats.get("max"),
            "effective_resistance_mean": stats.get("mean"),
            "effective_resistance_median": stats.get("median"),
        })
    return out

def _collect_fenchel_energy_stats() -> List[Dict[str, Any]]:
    index = _load_fenchel_energy_index()
    out: List[Dict[str, Any]] = []
    for entry in index:
        # cada entrada é o próprio payload; mas também salvamos arquivos por grafo
        # tentamos carregar o arquivo por graph_id se existir
        gid = entry.get("graph_id")
        path_json = (RESULTS_PHYSICS_DIR / "fenchel_energy" / f"{gid}.json")
        if path_json.exists():
            data = read_json(path_json)
        else:
            data = entry
        out.append({
            "graph_id": data.get("graph_id"),
            "n": data.get("n"),
            "rho": data.get("rho"),
            "fenchel_energy": data.get("energy"),
        })
    return out

def build_tables() -> Dict[str, Any]:
    ensure_dir(REPORTS_DIR)
    spectrum = _load_spectrum_summary()
    eff_res_stats = _collect_effective_resistance_stats()
    fenchel_stats = _collect_fenchel_energy_stats()

    # Índices por graph_id
    spec_by_id: Dict[str, Dict[str, Any]] = {r.get("graph_id"): r for r in spectrum}
    eff_by_id: Dict[str, Dict[str, Any]] = {r.get("graph_id"): r for r in eff_res_stats}
    fen_by_id: Dict[str, Dict[str, Any]] = {r.get("graph_id"): r for r in fenchel_stats}

    # União de ids
    ids = sorted(set(spec_by_id.keys()) | set(eff_by_id.keys()) | set(fen_by_id.keys()))

    # Tabela CSV consolidada
    csv_path = REPORTS_DIR / "summary_tables.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "graph_id",
            "n",
            "rho",
            "lambda1",
            "k_used",
            "effective_resistance_min",
            "effective_resistance_max",
            "effective_resistance_mean",
            "effective_resistance_median",
            "fenchel_energy",
        ])
        for gid in ids:
            s = spec_by_id.get(gid, {})
            e = eff_by_id.get(gid, {})
            fe = fen_by_id.get(gid, {})
            w.writerow([
                gid,
                s.get("n") or e.get("n") or fe.get("n"),
                s.get("rho") or e.get("rho") or fe.get("rho"),
                s.get("lambda1"),
                s.get("k_used"),
                e.get("effective_resistance_min"),
                e.get("effective_resistance_max"),
                e.get("effective_resistance_mean"),
                e.get("effective_resistance_median"),
                fe.get("fenchel_energy"),
            ])

    # Também salvar em JSON e YAML
    records: List[Dict[str, Any]] = []
    for gid in ids:
        s = spec_by_id.get(gid, {})
        e = eff_by_id.get(gid, {})
        fe = fen_by_id.get(gid, {})
        records.append({
            "graph_id": gid,
            "n": s.get("n") or e.get("n") or fe.get("n"),
            "rho": s.get("rho") or e.get("rho") or fe.get("rho"),
            "spectrum": {
                "lambda1": s.get("lambda1"),
                "k_used": s.get("k_used"),
                "tol": s.get("tol"),
                "notes": s.get("notes"),
            },
            "effective_resistance": {
                "min": e.get("effective_resistance_min"),
                "max": e.get("effective_resistance_max"),
                "mean": e.get("effective_resistance_mean"),
                "median": e.get("effective_resistance_median"),
            },
            "fenchel_energy": fe.get("fenchel_energy"),
        })

    write_json(REPORTS_DIR / "summary_tables.json", {"results": records}, indent=2)
    write_yaml(REPORTS_DIR / "summary_tables.yaml", {"results": records})

    return {"results": records}

if __name__ == "__main__":
    out = build_tables()
    print(f"Tabelas consolidadas geradas para {len(out['results'])} grafos. Saída em {REPORTS_DIR}")
