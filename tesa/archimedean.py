# =============================================================================
# tesa.archimedean
#
# Propósito:
# - Fornecer a camada arquimediana C_∞ para a Máquina TESA, com API estável,
#   relatórios de normalização (média zero) e verificações básicas.
#
# O que este módulo faz hoje (placeholder controlado e auditável):
# - compute_C_infty: retorna C_∞ a partir de parâmetros epsilon (C_epsilon),
#   podendo validar média zero e informar um sup_norm_bound opcional.
# - check_mean_zero: utilitário para verificar numericamente se a média é ~0.
# - estimate_sup_norm: estima norma L∞ de um potencial discreto/amostrado.
# - assemble_arch_report: consolida relatório com flags e notas.
#
# Como evoluir:
# - Substituir o placeholder por cálculo real do potencial de Green contínuo
#   na métrica admissível, garantindo normalização ∫ G dμ = 0 e cotas L∞.
# - Integrar kernels conhecidos (curvas de gênero g≥1), discretizações em malha,
#   quadraturas e certificados de erro.
#
# API estável esperada pelo orquestrador:
#   compute_C_infty(L_data: dict, metric_data: dict, epsilon_params: dict) -> dict
#   Retorno: {"C_infty": float, "report": dict}
#
# Licença:
# - MIT
# =============================================================================

from typing import Dict, Any, Optional, Sequence
import math


def check_mean_zero(samples: Optional[Sequence[float]], atol: float = 1e-9) -> Dict[str, Any]:
    """
    Verifica se a média dos samples está próxima de zero (métrica com normalização de média zero).
    Retorna estatísticas simples e um flag booleano.
    """
    if samples is None or len(samples) == 0:
        return {
            "mean": None,
            "std": None,
            "n": 0,
            "mean_zero_ok": True,  # assume ok quando não há amostras
            "atol": atol,
            "notes": "Sem amostras fornecidas; assumindo normalização correta."
        }
    n = len(samples)
    mean = sum(samples) / float(n)
    # variância populacional simples
    var = sum((x - mean) ** 2 for x in samples) / float(n)
    std = math.sqrt(var)
    mean_zero_ok = abs(mean) <= float(atol)
    return {
        "mean": mean,
        "std": std,
        "n": n,
        "mean_zero_ok": mean_zero_ok,
        "atol": atol,
        "notes": "Média considerada zero se |mean| <= atol."
    }


def estimate_sup_norm(samples: Optional[Sequence[float]]) -> Optional[float]:
    """
    Estima a norma L∞ (supremo) a partir de amostras discretas do potencial.
    Se não houver amostras, retorna None.
    """
    if samples is None or len(samples) == 0:
        return None
    # sup de |x|
    return max(abs(x) for x in samples)


def assemble_arch_report(
    mean_zero_report: Dict[str, Any],
    sup_norm_bound: Optional[float],
    used_C_epsilon: float,
    method: str = "placeholder-epsilon-control"
) -> Dict[str, Any]:
    """
    Consolida relatório arquimediano para auditoria.
    """
    report = {
        "mean_zero_ok": bool(mean_zero_report.get("mean_zero_ok", True)),
        "mean_zero_stats": {
            "mean": mean_zero_report.get("mean"),
            "std": mean_zero_report.get("std"),
            "n": mean_zero_report.get("n"),
            "atol": mean_zero_report.get("atol"),
        },
        "sup_norm_bound": sup_norm_bound,
        "method": method,
        "notes": (
            "C_∞ controlado por parâmetro C_epsilon. "
            "Substituir por cálculo com Green contínuo e normalização admissível."
        ),
        "C_epsilon_used": used_C_epsilon,
    }
    return report


def compute_C_infty(
    L_data: Dict[str, Any],
    metric_data: Dict[str, Any],
    epsilon_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Placeholder arquimediano auditável.

    Entradas:
    - L_data: dados do feixe/linha (ex.: {"bundle": "Neron-Tate"}), livre.
    - metric_data: metadados da métrica, podendo conter:
        - "mean_zero": bool indicando se a normalização foi imposta externamente.
        - "potential_samples": lista de amostras do potencial contínuo (opcional).
        - "mean_atol": tolerância absoluta para checagem de média zero (opcional).
    - epsilon_params:
        - "C_epsilon": valor que será usado como C_∞ (default 1.0).
        - "sup_norm_bound": cota superior confiável para o sup |G| (opcional).
        - "override_with_sup": se True e houver samples, define C_∞ = sup_norm_estimada.

    Saída:
    {
      "C_infty": float,
      "report": {
         "mean_zero_ok": bool,
         "mean_zero_stats": {...},
         "sup_norm_bound": float|None,
         "method": "placeholder-epsilon-control" | "...",
         "notes": "...",
         "C_epsilon_used": float
      }
    }
    """
    # Parâmetros de controle
    C_epsilon = float(epsilon_params.get("C_epsilon", 1.0))
    sup_norm_bound = epsilon_params.get("sup_norm_bound", None)
    override_with_sup = bool(epsilon_params.get("override_with_sup", False))

    # Checagem de média zero (se houver amostras)
    pot_samples = metric_data.get("potential_samples")
    mean_atol = float(metric_data.get("mean_atol", 1e-9))
    mean_zero_report = check_mean_zero(pot_samples, atol=mean_atol)

    # Estimativa de sup a partir de amostras (se fornecidas)
    sup_est = estimate_sup_norm(pot_samples)

    # Escolha do C_∞:
    # - Se override_with_sup e sup_est existir, prioriza a evidência empírica
    # - Caso contrário, usa C_epsilon (parametrização externa)
    if override_with_sup and sup_est is not None:
        C_infty = float(sup_est)
        method = "override-with-sup-estimate"
        # Se sup_norm_bound for fornecido, adote o menor entre os dois como cota conservadora
        if sup_norm_bound is not None:
            try:
                sup_val = float(sup_norm_bound)
                C_infty = float(min(C_infty, sup_val))
                method += " (min-with-sup_norm_bound)"
            except Exception:
                # ignora conversão falha de sup_norm_bound
                pass
    else:
        C_infty = C_epsilon
        method = "placeholder-epsilon-control"
        # Se houver sup_norm_bound numérico e for menor, podemos adotar a mais apertada
        if sup_norm_bound is not None:
            try:
                sup_val = float(sup_norm_bound)
                if sup_val < C_infty:
                    C_infty = float(sup_val)
                    method = "sup_norm_bound-tightened"
            except Exception:
                # ignora conversão falha de sup_norm_bound
                pass

    report = assemble_arch_report(
        mean_zero_report=mean_zero_report,
        sup_norm_bound=(float(sup_norm_bound) if isinstance(sup_norm_bound, (int, float)) else None),
        used_C_epsilon=float(C_epsilon),
        method=method
    )

    # Se metric_data tiver um flag explícito de mean_zero=False, sinalizar no report
    if "mean_zero" in metric_data and not bool(metric_data["mean_zero"]):
        report["mean_zero_ok"] = False
        note = report.get("notes", "")
        report["notes"] = (note + " | Aviso: metric_data.mean_zero=False").strip()

    return {"C_infty": float(C_infty), "report": report}
