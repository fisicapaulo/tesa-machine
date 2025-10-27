# =============================================================================
# tesa.io_report
#
# Propósito:
# - Utilitários de entrada/saída e geração de relatórios para a Máquina TESA:
#   * salvar/ler JSON com segurança;
#   * exportar resultados locais em CSV;
#   * gerar gráficos simples (matplotlib opcional);
#   * compor e salvar relatórios de alto nível (integra com global_orchestrator).
#
# Observação:
# - Este módulo evita dependências pesadas: matplotlib é opcional.
# - Todas as funções são "best-effort": falhas são tratadas com mensagens seguras.
#
# API sugerida:
# - save_json(data, path) -> str
# - load_json(path) -> dict|list|None
# - export_locals_csv(local_results, path) -> str
# - plot_local_constants(local_results, path, title=None) -> Optional[str]
# - summarize_locals(local_results) -> dict
# - write_text_report(text, path) -> str
# - compose_text_report_global(info, local_results) -> str
#
# Licença:
# - MIT
# =============================================================================

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import os
import csv
import json
import math
import datetime


def ensure_dir(path: str) -> None:
    """
    Garante que o diretório do arquivo exista.
    """
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def save_json(data: Union[Dict[str, Any], List[Any]], path: str, indent: int = 2) -> str:
    """
    Salva dados em JSON com indentação opcional e UTF-8.
    Retorna o caminho salvo.
    """
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    return path


def load_json(path: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """
    Carrega JSON de 'path'. Retorna None se falhar.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def export_locals_csv(local_results: List[Dict[str, Any]], path: str) -> str:
    """
    Exporta resultados locais em CSV.
    Colunas padrão (se existirem): place,name,i0,conductance,K_v,f_v_tame,f_v,E_fenchel,C_Type,n
    Outras chaves são preservadas, mas a ordem das padrão vem primeiro.
    """
    ensure_dir(path)
    default_cols = [
        "place", "name", "i0", "conductance", "K_v",
        "f_v_tame", "f_v", "E_fenchel", "C_type", "n"
    ]

    # Descobrir chaves extras
    extra_keys = set()
    for r in local_results:
        extra_keys.update(r.keys())
    # Remover duplicadas das padrão e manter ordem
    extra_cols = [k for k in sorted(extra_keys) if k not in default_cols]

    fieldnames = default_cols + extra_cols

    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in local_results:
            row = {}
            for k in fieldnames:
                row[k] = r.get(k, "")
            writer.writerow(row)
    return path


def try_import_matplotlib():
    """
    Tenta importar matplotlib de forma segura.
    Retorna (plt, ok: bool).
    """
    try:
        import matplotlib.pyplot as plt  # type: ignore
        return plt, True
    except Exception:
        return None, False


def plot_local_constants(
    local_results: List[Dict[str, Any]],
    path: str,
    title: Optional[str] = None
) -> Optional[str]:
    """
    Gera um gráfico de barras de C_type por 'place' ou índice.
    Salva a figura em 'path' se matplotlib estiver disponível.
    Retorna o caminho salvo ou None.
    """
    plt, ok = try_import_matplotlib()
    if not ok:
        return None

    ensure_dir(path)

    # Preparar dados
    labels = []
    values = []
    for idx, r in enumerate(local_results):
        place = str(r.get("place", idx))
        ctype = r.get("C_type", None)
        try:
            val = float(ctype) if ctype is not None else 0.0
        except Exception:
            val = 0.0
        labels.append(place)
        values.append(val)

    # Plot
    fig, ax = plt.subplots(figsize=(max(6, min(12, 0.6 * max(3, len(values)))), 4))
    ax.bar(range(len(values)), values, color="#3B82F6")
    ax.set_xlabel("place")
    ax.set_ylabel("C_type")
    ax.set_title(title or "TESA: C_type por lugar")
    ax.set_xticks(range(len(values)))
    # Limitar número de rótulos para não poluir
    if len(labels) > 20:
        step = max(1, len(labels) // 20)
        show_idx = set(range(0, len(labels), step))
        ax.set_xticklabels([labels[i] if i in show_idx else "" for i in range(len(labels))], rotation=45, ha="right")
    else:
        ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def summarize_locals(local_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcula estatísticas simples sobre os C_type locais:
      - n, soma, média, desvio padrão, min, max; e top_k índices (por magnitude).
    """
    vals: List[float] = []
    for r in local_results:
        try:
            vals.append(float(r.get("C_type", 0.0)))
        except Exception:
            vals.append(0.0)
    n = len(vals)
    s = sum(vals)
    mean = s / n if n > 0 else 0.0
    var = sum((x - mean) ** 2 for x in vals) / n if n > 0 else 0.0
    std = math.sqrt(var)
    vmin = min(vals) if n > 0 else 0.0
    vmax = max(vals) if n > 0 else 0.0

    # top contribuintes por valor absoluto
    indexed = list(enumerate(vals))
    indexed.sort(key=lambda t: abs(t[1]), reverse=True)
    top_k = indexed[: min(10, len(indexed))]

    return {
        "n": n,
        "sum": s,
        "mean": mean,
        "std": std,
        "min": vmin,
        "max": vmax,
        "top_k_indices": [i for i, _ in top_k],
        "top_k_values": [v for _, v in top_k],
    }


def compose_text_report_global(info: Dict[str, Any], local_results: List[Dict[str, Any]]) -> str:
    """
    Constrói um relatório textual simples e auto-contido para o nível global.
    Compatível com o formato de summarize_global do orquestrador.
    """
    lines: List[str] = []
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    lines.append("=== TESA — Relatório Global (io_report) ===")
    lines.append(f"timestamp_utc: {now}")
    g = info.get("inputs", {}).get("g", "?")
    lines.append(f"g: {g}")
    lines.append(f"delta (Axioma 2): {info.get('delta')}")
    lines.append(f"Soma C_Type: {info.get('C_types_sum')}")
    lines.append(f"C_infty: {info.get('C_infty')}")
    lines.append(f"C_Global: {info.get('C_global')}")
    lines.append("— Certificados e relatórios —")
    lines.append(f"delta_certificate: {info.get('delta_certificate')}")
    lines.append(f"C_infty_report: {info.get('C_infty_report')}")
    lines.append("— Locais —")
    if not local_results:
        lines.append("(sem resultados locais)")
    else:
        lines.append("place | name | i0 | c | K_v | f_v^tame | f_v | E_fenchel | C_Type | n")
        for r in local_results:
            place = r.get("place", "?")
            name = r.get("name", "?")
            i0 = r.get("i0", "?")
            c = r.get("conductance", "?")
            Kv = r.get("K_v", "?")
            ft = r.get("f_v_tame", "?")
            fv = r.get("f_v", "?")
            Ef = r.get("E_fenchel", "?")
            Ct = r.get("C_type", "?")
            n = r.get("n", "?")
            lines.append(f"{place} | {name} | {i0} | {c} | {Kv} | {ft} | {fv} | {Ef} | {Ct} | {n}")
    eps = info.get("inputs", {}).get("epsilon_params", {})
    err_sum = info.get("inputs", {}).get("err_locals_sum", 0.0)
    lines.append("— Parâmetros —")
    lines.append(f"epsilon_params: {eps}")
    lines.append(f"err_locals_sum: {err_sum}")
    lines.append("=== Fim do Relatório ===")
    return "\n".join(lines)


def write_text_report(text: str, path: str) -> str:
    """
    Salva um relatório de texto simples em 'path'.
    """
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def quick_bundle_outputs(
    info: Dict[str, Any],
    local_results: List[Dict[str, Any]],
    out_dir: str = "outputs",
    prefix: Optional[str] = None,
    make_plot: bool = True
) -> Dict[str, Optional[str]]:
    """
    Cria rapidamente um pacote de saídas:
      - JSON com 'info'
      - CSV com locais
      - TXT com relatório global
      - PNG com gráfico de C_type (se matplotlib disponível e make_plot=True)

    Parâmetros:
      - out_dir: diretório base para salvar arquivos.
      - prefix: prefixo do nome dos arquivos (ex.: "g1"); se None, usa "tesa".
      - make_plot: se False, não tenta gerar gráfico.

    Retorno:
      {
        "json_info": str|None,
        "csv_locals": str|None,
        "txt_report": str|None,
        "png_plot": str|None
      }
    """
    base = prefix or "tesa"
    out_paths: Dict[str, Optional[str]] = {
        "json_info": None,
        "csv_locals": None,
        "txt_report": None,
        "png_plot": None,
    }

    # JSON
    try:
        json_path = os.path.join(out_dir, f"{base}_global_info.json")
        save_json(info, json_path)
        out_paths["json_info"] = json_path
    except Exception:
        out_paths["json_info"] = None

    # CSV
    try:
        csv_path = os.path.join(out_dir, f"{base}_locals.csv")
        export_locals_csv(local_results, csv_path)
        out_paths["csv_locals"] = csv_path
    except Exception:
        out_paths["csv_locals"] = None

    # TXT
    try:
        text = compose_text_report_global(info, local_results)
        txt_path = os.path.join(out_dir, f"{base}_global_report.txt")
        write_text_report(text, txt_path)
        out_paths["txt_report"] = txt_path
    except Exception:
        out_paths["txt_report"] = None

    # PNG
    if make_plot:
        try:
            png_path = os.path.join(out_dir, f"{base}_locals_plot.png")
            ret = plot_local_constants(local_results, png_path, title=f"{base}: C_type por lugar")
            out_paths["png_plot"] = ret
        except Exception:
            out_paths["png_plot"] = None

    return out_paths


# Exemplo de uso programático (não executado automaticamente):
# info = {...}  # retornado pelo orquestrador
# local_results = [...]
# outputs = quick_bundle_outputs(info, local_results, out_dir="outputs", prefix="g1")
