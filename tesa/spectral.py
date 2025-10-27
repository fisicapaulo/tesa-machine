# =============================================================================
# tesa.spectral.py
#
# Propósito:
# - Fornecer a camada espectral para computar um δ (Axioma 2) auditável
#   a partir de dados da família/curva, com APIs estáveis para o orquestrador.
#
# O que este módulo faz hoje (placeholder controlado e auditável):
# - compute_delta: produz um δ ∈ [0, 1) a partir de:
#     * family_data["delta_lower_bound"] (se fornecido),
#     * ou uma estima discreta via pseudo-espectro (samples),
#     * com clipping e relatórios de estabilidade.
# - Utilitários:
#     * estimate_spectral_gap: computa "gap" mínimo de uma matriz Laplaciana
#       (segunda menor autovalor de um Laplaciano não normalizado).
#     * normalize_delta: normaliza δ para o intervalo [0, 1) com tolerância.
#     * assemble_delta_certificate: cria certificado auditável do δ.
#
# Como evoluir:
# - Integrar operadores de Laplaciano contínuo/hiperbólico, Núcleo de Green,
#   e certificados rigorosos (interval arithmetic).
# - Conectar com bibliotecas numéricas quando permitido (scipy.sparse.linalg),
#   mantendo fallback puro-Python com Rayleigh quotients para matrizes pequenas.
#
# API estável esperada pelo orquestrador:
#   compute_delta(g: int, family_data: dict) -> dict
#   Retorno: {"delta": float, "certificate": dict}
#
# Licença:
# - MIT
# =============================================================================

from typing import Dict, Any, List, Optional, Sequence, Tuple
import math


def normalize_delta(value: float, eps: float = 1e-12) -> float:
    """
    Normaliza δ para o intervalo [0, 1) com margem de segurança.
    Clipa negativos para 0.0 e valores >= 1 - eps para 1 - eps.
    """
    if math.isnan(value) or math.isinf(value):
        return 0.0
    v = float(value)
    if v < 0.0:
        return 0.0
    upper = 1.0 - float(eps)
    if v >= upper:
        return upper
    return v


def estimate_spectral_gap(
    laplacian: Sequence[Sequence[float]]
) -> Optional[float]:
    """
    Estima a segunda menor autovalor (λ2) de um Laplaciano simétrico real.
    Requisitos:
      - 'laplacian' é uma matriz quadrada (lista de listas) simétrica.
      - Laplaciano não-normalizado esperado (linhas somam 0).
    Observações:
      - Método simples e robusto para matrizes pequenas: varre subespaços
        ortogonais ao vetor constante usando uma base canônica corrigida.
      - Para casos maiores, substitua por um solver eigen (quando permitido).
    Retorna:
      - λ2 ≥ 0 se conseguir estimar; None se entrada vazia/degenerada.
    """
    # Verificações básicas
    if laplacian is None:
        return None
    n = len(laplacian)
    if n == 0:
        return None
    for row in laplacian:
        if len(row) != n:
            return None

    # Funções auxiliares de álgebra linear (puro Python)
    def dot(u: Sequence[float], v: Sequence[float]) -> float:
        return sum(ux * vx for ux, vx in zip(u, v))

    def matvec(A: Sequence[Sequence[float]], x: Sequence[float]) -> List[float]:
        return [sum(A[i][j] * x[j] for j in range(n)) for i in range(n)]

    def norm2(x: Sequence[float]) -> float:
        return math.sqrt(dot(x, x))

    # Vetor constante (autoespaço para λ=0)
    one = [1.0] * n
    one_norm = norm2(one)
    if one_norm == 0.0:
        return None
    one_unit = [v / one_norm for v in one]

    # Construir uma família de vetores de teste ortogonais a one_unit
    # Base canônica e projeção ortogonal
    test_vectors: List[List[float]] = []
    for k in range(n):
        e = [0.0] * n
        e[k] = 1.0
        # projeta e em ortogonal ao vetor constante
        proj = dot(e, one_unit)
        v = [e[i] - proj * one_unit[i] for i in range(n)]
        nv = norm2(v)
        if nv > 0:
            test_vectors.append([vi / nv for vi in v])

    if not test_vectors:
        return None

    # Estimativa via quociente de Rayleigh: R(v) = (v^T L v) / (v^T v)
    # Aqui v está normalizado, então R(v) = v^T L v
    rayleigh_vals: List[float] = []
    for v in test_vectors:
        Lv = matvec(laplacian, v)
        r = dot(v, Lv)
        # Laplaciano ideal: r >= 0, mas ruído numérico pode dar negativo pequeno
        rayleigh_vals.append(max(0.0, float(r)))

    # A melhor estimativa para λ2 é o mínimo quociente de Rayleigh no subespaço ortogonal
    lam2_est = min(rayleigh_vals) if rayleigh_vals else None
    return lam2_est


def assemble_delta_certificate(
    method: str,
    raw_value: float,
    normalized_delta: float,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Consolida o certificado/relatório para δ.
    """
    return {
        "method": method,
        "raw_value": raw_value,
        "normalized": normalized_delta,
        "context": context,
        "notes": (
            "δ normalizado para [0,1). Substitua por cota espectral rigorosa "
            "quando disponível (ex.: λ2/Λ, isoperimétrico, ou Axioma 2 analítico)."
        ),
    }


def compute_delta(g: int, family_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder espectral auditável para δ (Axioma 2).

    Estratégias suportadas (em ordem de precedência):
      1) Se family_data contém "delta_lower_bound" (numérico), usa-o após normalização.
      2) Se family_data contém "laplacian" (matriz) e "lambda_scale" (positivo),
         estima λ2 e define δ_raw = min(1, λ2 / lambda_scale).
      3) Se family_data contém "spectral_samples" (valores >0), usa uma heurística
         δ_raw = min(1, min(samples) / max(samples)).
      4) Fallback: δ_raw = 0.0.

    Parâmetros opcionais:
      - "clip_eps": tolerância para clipping superior de δ (default 1e-12).
      - "force_cap": valor máximo manual para δ antes da normalização (opcional).

    Retorno:
      {
        "delta": float,
        "certificate": {...}
      }
    """
    clip_eps = float(family_data.get("clip_eps", 1e-12))

    # 1) Bound explícito fornecido
    if "delta_lower_bound" in family_data:
        try:
            raw = float(family_data["delta_lower_bound"])
        except Exception:
            raw = 0.0
        # Aplicar cap se fornecido
        if "force_cap" in family_data:
            try:
                cap = float(family_data["force_cap"])
                raw = min(raw, cap)
            except Exception:
                pass
        delta_norm = normalize_delta(raw, eps=clip_eps)
        cert = assemble_delta_certificate(
            method="explicit-lower-bound",
            raw_value=raw,
            normalized_delta=delta_norm,
            context={"g": g, "source": "family_data.delta_lower_bound"}
        )
        return {"delta": delta_norm, "certificate": cert}

    # 2) Estimativa via Laplaciano discreto
    lap = family_data.get("laplacian", None)
    lambda_scale = family_data.get("lambda_scale", None)
    if lap is not None and lambda_scale is not None:
        try:
            lam_scale = float(lambda_scale)
            if lam_scale <= 0:
                raise ValueError
            lam2 = estimate_spectral_gap(lap)
            if lam2 is None:
                raw = 0.0
            else:
                raw = min(1.0, float(lam2) / lam_scale)
        except Exception:
            raw = 0.0
        # cap opcional
        if "force_cap" in family_data:
            try:
                cap = float(family_data["force_cap"])
                raw = min(raw, cap)
            except Exception:
                pass
        delta_norm = normalize_delta(raw, eps=clip_eps)
        cert = assemble_delta_certificate(
            method="discrete-laplacian-ratio",
            raw_value=raw,
            normalized_delta=delta_norm,
            context={
                "g": g,
                "lambda_scale": lambda_scale,
                "lam2_estimate": lam2,
                "matrix_size": len(lap) if isinstance(lap, (list, tuple)) else None
            }
        )
        return {"delta": delta_norm, "certificate": cert}

    # 3) Heurística via amostras espectrais positivas
    samples = family_data.get("spectral_samples", None)
    if isinstance(samples, (list, tuple)) and len(samples) > 0:
        # Considera apenas valores positivos
        pos = [float(x) for x in samples if isinstance(x, (int, float)) and float(x) > 0.0]
        if len(pos) >= 2:
            smin, smax = min(pos), max(pos)
            raw = 0.0 if smax == 0.0 else min(1.0, smin / smax)
        elif len(pos) == 1:
            # Com um único valor, δ_raw é 1 "teoricamente", mas adotamos algo conservador
            raw = 0.5
        else:
            raw = 0.0
        # cap opcional
        if "force_cap" in family_data:
            try:
                cap = float(family_data["force_cap"])
                raw = min(raw, cap)
            except Exception:
                pass
        delta_norm = normalize_delta(raw, eps=clip_eps)
        cert = assemble_delta_certificate(
            method="spectral-samples-heuristic",
            raw_value=raw,
            normalized_delta=delta_norm,
            context={"g": g, "n_samples": len(pos)}
        )
        return {"delta": delta_norm, "certificate": cert}

    # 4) Fallback
    raw = 0.0
    delta_norm = normalize_delta(raw, eps=clip_eps)
    cert = assemble_delta_certificate(
        method="fallback-zero",
        raw_value=raw,
        normalized_delta=delta_norm,
        context={"g": g}
    )
    return {"delta": delta_norm, "certificate": cert}
