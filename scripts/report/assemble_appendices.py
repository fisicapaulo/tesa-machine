from pathlib import Path
from typing import Any, Dict, List, Optional

import json
import yaml

from scripts.common.io_utils import (
    read_json,
    read_yaml,
    ensure_dir,
)

RESULTS_DIR = Path("tesa-machine/results")
REPORTS_DIR = Path("tesa-machine/reports")
TABLES_DIR = REPORTS_DIR / "tables"
PLOTS_DIR = REPORTS_DIR / "plots"
APPENDICES_DIR = REPORTS_DIR / "appendices"

def _safe_read(path: Path) -> Optional[Dict[str, Any] | List[Any]]:
    try:
        if path.suffix.lower() == ".json":
            return read_json(path)
        elif path.suffix.lower() in (".yml", ".yaml"):
            return read_yaml(path)
    except Exception:
        return None
    return None

def _gather_spectrum_material() -> Dict[str, Any]:
    out: Dict[str, Any] = {"index": None, "items": []}
    # índices e resumos
    idx_json = PLOTS_DIR / "spectrum_plots_index.json"
    idx_yaml = PLOTS_DIR / "spectrum_plots_index.yaml"
    sum_json = RESULTS_DIR / "spectrum" / "summary_spectrum.json"
    sum_yaml = RESULTS_DIR / "spectrum" / "summary_spectrum.yaml"

    out["index"] = _safe_read(idx_json) or _safe_read(idx_yaml)
    summary = _safe_read(sum_json) or _safe_read(sum_yaml)

    # itens por grafo a partir do índice de plots
    items: List[Dict[str, Any]] = []
    if out["index"] and isinstance(out["index"], dict):
        for rec in out["index"].get("results", []):
            gid = rec.get("graph_id")
            paths = rec.get("paths", {})
            stats = rec.get("stats", {})
            # juntar com lambda1 do summary, se disponível
            if summary and isinstance(summary, dict):
                for srec in summary.get("results", []):
                    if srec.get("graph_id") == gid:
                        stats = {**srec, **stats}
                        break
            items.append({
                "graph_id": gid,
                "paths": {
                    "spectrum": paths.get("spectrum"),
                    "hist": paths.get("hist"),
                    "ratio": paths.get("ratio"),
                },
                "stats": stats,
            })
    out["items"] = items
    return out

def _gather_tables() -> Dict[str, Any]:
    # Carrega tabelas consolidadas (csv, json, yaml)
    summary_json = TABLES_DIR / "summary_tables.json"
    summary_yaml = TABLES_DIR / "summary_tables.yaml"
    csv_path = TABLES_DIR / "summary_tables.csv"

    data = _safe_read(summary_json) or _safe_read(summary_yaml) or {"results": []}
    return {
        "summary": data,
        "csv_path": str(csv_path) if csv_path.exists() else None,
    }

def _gather_physics_indexes() -> Dict[str, Any]:
    eff_json = RESULTS_DIR / "physics" / "effective_resistance_index.json"
    eff_yaml = RESULTS_DIR / "physics" / "effective_resistance_index.yaml"
    fen_json = RESULTS_DIR / "physics" / "fenchel_energy_index.json"
    fen_yaml = RESULTS_DIR / "physics" / "fenchel_energy_index.yaml"

    eff = _safe_read(eff_json) or _safe_read(eff_yaml) or {"results": []}
    fen = _safe_read(fen_json) or _safe_read(fen_yaml) or {"results": []}
    return {"effective_resistance": eff, "fenchel_energy": fen}

def assemble_appendices(limit_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    ensure_dir(APPENDICES_DIR)

    spectrum = _gather_spectrum_material()
    tables = _gather_tables()
    physics = _gather_physics_indexes()

    # Filtrar por graph_id se solicitado
    def _filter_by_ids(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not limit_ids:
            return items
        return [x for x in items if x.get("graph_id") in limit_ids]

    spectrum_items = _filter_by_ids(spectrum.get("items", []))
    summary_records = _filter_by_ids((tables.get("summary", {}) or {}).get("results", []))

    # Estrutura do apêndice
    appendix = {
        "spectrum": {
            "index": spectrum.get("index"),
            "items": spectrum_items,
        },
        "tables": {
            "summary": {"results": summary_records},
            "csv_path": tables.get("csv_path"),
        },
        "physics_indexes": physics,
    }

    # Caminhos de saída
    out_dir = ensure_dir(APPENDICES_DIR)
    out_json = out_dir / "appendices_index.json"
    out_yaml = out_dir / "appendices_index.yaml"

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(appendix, f, indent=2, ensure_ascii=False)
    with open(out_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(appendix, f, sort_keys=False, allow_unicode=True)

    return appendix

if __name__ == "__main__":
    out = assemble_appendices()
    num_specs = len(out.get("spectrum", {}).get("items", []))
    num_tabs = len(out.get("tables", {}).get("summary", {}).get("results", []))
    print(f"Apêndices montados. Espectros: {num_specs}, registros em tabelas: {num_tabs}. Saída em {APPENDICES_DIR}")