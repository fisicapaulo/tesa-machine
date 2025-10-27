# =============================================================================
# tesa.global_orchestrator
#
# Propósito:
# - Orquestrar a Soma Global TESA e produzir um relatório auditável.
# - δ (Axioma 2) + Σ_v C_Type,v (módulo local) + C_∞ (arquimediano) + resíduos
#   → C_Global e desigualdade h_L(P) ≤ (1 − δ)·m_D(P) + C_Global.
#
# Novidades:
# - summarize_global(...) gera um relatório de texto consolidado.
# - save_summary_txt(...) grava o relatório em outputs/global_report.txt (ou caminho dado).
# - run_tesa_pipeline(..., verbose=True, save_report_path=...) imprime e/ou salva o relatório.
#
# Integração:
# - local_results: lista de dicts com chave "C_type" (de tesa.local_c_type).
# - delta_computer e arch_computer: funções externas conforme APIs combinadas.
#
# Licença:
# - MIT (ajuste conforme necessário).
# =============================================================================

from typing import List, Dict, Any
import os


def sum_C_type(local_results: List[Dict[str, Any]]) -> float:
    return float(sum(r.get("C_type", 0.0) for r in local_results))


def assemble_global_constant(
    delta: float,
    C_infty: float,
    C_types_sum: float,
    err_locals_sum: float = 0.0,
) -> float:
    return float(C_infty + C_types_sum + err_locals_sum)


def tesa_global_bound(h_L: float, m_D: float, delta: float, C_global: float) -> float:
    return (1.0 - float(delta)) * float(m_D) + float(C_global)


def summarize_global(info: Dict[str, Any], local_results: List[Dict[str, Any]]) -> str:
    """
    Retorna um relatório textual consolidado do resultado global e dos locais.
    """
    lines = []
    lines.append("=== TESA — Relatório Global ===")
    lines.append(f"g: {info.get('inputs', {}).get('g', '?')}")
    lines.append(f"delta (Axioma 2): {info.get('delta')}")
    lines.append(f"Soma C_Type: {info.get('C_types_sum')}")
    lines.append(f"C_infty: {info.get('C_infty')}")
    lines.append(f"C_Global: {info.get('C_global')}")
    lines.append("— Certificados e relatórios —")
    lines.append(f"delta_certificate: {info.get('delta_certificate')}")
    lines.append(f"C_infty_report: {info.get('C_infty_report')}")
    # Resumo local por lugar (se houver 'place' e 'name')
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
    # Parâmetros de entrada relevantes
    eps = info.get("inputs", {}).get("epsilon_params", {})
    err_sum = info.get("inputs", {}).get("err_locals_sum", 0.0)
    lines.append("— Parâmetros —")
    lines.append(f"epsilon_params: {eps}")
    lines.append(f"err_locals_sum: {err_sum}")
    lines.append("=== Fim do Relatório ===")
    return "\n".join(lines)


def save_summary_txt(report: str, out_path: str = "outputs/global_report.txt") -> str:
    """
    Salva o relatório textual em arquivo e retorna o caminho salvo.
    """
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    return out_path


def run_tesa_pipeline(
    g: int,
    family_data: Dict[str, Any],
    local_results: List[Dict[str, Any]],
    L_data: Dict[str, Any],
    metric_data: Dict[str, Any],
    epsilon_params: Dict[str, Any],
    delta_computer,   # compute_delta
    arch_computer,    # compute_C_infty
    err_locals_sum: float = 0.0,
    verbose: bool = False,
    save_report_path: str | None = None,
) -> Dict[str, Any]:
    """
    Pipeline principal:
    - δ via delta_computer
    - Σ C_Type via local_results
    - C_∞ via arch_computer
    - C_Global = C_∞ + Σ C_Type + err_locals_sum
    - Opcional: imprime e/ou salva relatório consolidado
    """
    delta_info = delta_computer(g, family_data)
    delta = float(delta_info.get("delta", 0.0))

    C_types_sum = sum_C_type(local_results)

    C_inf_info = arch_computer(L_data, metric_data, epsilon_params)
    C_infty = float(C_inf_info.get("C_infty", 0.0))

    C_global = assemble_global_constant(delta, C_infty, C_types_sum, float(err_locals_sum))

    info = {
        "delta": delta,
        "C_types_sum": C_types_sum,
        "C_infty": C_infty,
        "C_global": C_global,
        "delta_certificate": delta_info.get("certificate", {}),
        "C_infty_report": C_inf_info.get("report", {}),
        "inputs": {
            "g": g,
            "family_data": family_data,
            "epsilon_params": epsilon_params,
            "err_locals_sum": float(err_locals_sum),
        },
    }

    # Relatório
    if verbose or save_report_path:
        report = summarize_global(info, local_results)
        if verbose:
            print(report)
        if save_report_path:
            saved = save_summary_txt(report, save_report_path)
            if verbose:
                print(f"[Relatório salvo em] {saved}")

    return info


def evaluate_samples_against_bound(
    samples: List[Dict[str, Any]],
    delta: float,
    C_global: float,
) -> List[Dict[str, Any]]:
    """
    Para cada amostra com {'h_L', 'm_D'} adiciona {'RHS', 'ok'}.
    """
    out = []
    for s in samples:
        hL = float(s.get("h_L", 0.0))
        mD = float(s.get("m_D", 0.0))
        rhs = tesa_global_bound(hL, mD, delta, C_global)
        out.append({**s, "RHS": rhs, "ok": hL <= rhs})
    return out
