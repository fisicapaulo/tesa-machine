# =============================================================================
# tesa.config
#
# Propósito:
# - Centralizar parâmetros padrão e utilitários de configuração para a Máquina TESA.
# - Fornecer:
#     * Configuração global padrão (DEFAULT_CONFIG)
#     * Carregamento/merge de configurações de dicionários e arquivos JSON
#     * Leitura opcional de variáveis de ambiente (prefixo TESA_)
#     * Validação leve de campos conhecidos
#
# API sugerida:
# - get_default_config() -> dict
# - deep_update(base, override) -> dict
# - load_config_json(path) -> dict
# - apply_env_overrides(cfg, prefix="TESA_") -> dict
# - validate_config(cfg) -> dict
#
# Licença:
# - MIT
# =============================================================================

from typing import Any, Dict, List, Optional, Union
import os
import json


# Configuração padrão global
DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "0.1.0",
    "logging": {
        "level": "INFO",      # DEBUG, INFO, WARNING, ERROR
        "to_console": True,
        "to_file": False,
        "file_path": "outputs/tesa.log",
    },
    "paths": {
        "outputs_dir": "outputs",
        "cache_dir": "cache",
    },
    "archimedean": {
        "epsilon_params": {
            "C_epsilon": 1.0,
            "sup_norm_bound": None,
            "override_with_sup": False,
        },
        "mean_atol": 1e-9,
    },
    "spectral": {
        "clip_eps": 1e-12,
        "force_cap": None,
        # parâmetros para cálculo discreto (se usados)
        "lambda_scale": None,
    },
    "io": {
        "csv_export": True,
        "png_plot": True,
        "report_prefix": None,  # ex.: "g1"
    },
    "orchestrator": {
        "fail_fast": False,
        "max_workers": 1,   # manter determinismo por padrão
    },
}


def get_default_config() -> Dict[str, Any]:
    """
    Retorna uma cópia rasa da configuração padrão.
    """
    # Retornar cópia para evitar mutações externas
    import copy
    return copy.deepcopy(DEFAULT_CONFIG)


def deep_update(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Atualiza 'base' recursivamente com chaves de 'override' e retorna 'base'.
    - Dicionários são mergidos recursivamente;
    - Tipos escalares/listas substituem diretamente.
    """
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = v
    return base


def load_config_json(path: str) -> Dict[str, Any]:
    """
    Carrega um dicionário de configuração a partir de um arquivo JSON.
    Retorna {} se falhar.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _parse_env_value(val: str) -> Any:
    """
    Converte strings de ambiente em tipos básicos:
      - "true"/"false" (case-insensitive) -> bool
      - inteiros e floats
      - JSON válido (dict/list/number/bool/null)
      - fallback: string original
    """
    s = val.strip()
    low = s.lower()
    if low in ("true", "false"):
        return low == "true"
    # JSON tenta primeiro (permite listas/dicts)
    try:
        parsed = json.loads(s)
        return parsed
    except Exception:
        pass
    # int
    try:
        return int(s)
    except Exception:
        pass
    # float
    try:
        return float(s)
    except Exception:
        pass
    return s


def apply_env_overrides(cfg: Dict[str, Any], prefix: str = "TESA_") -> Dict[str, Any]:
    """
    Aplica overrides de variáveis de ambiente no dicionário 'cfg'.
    Convenção de chaves:
      - TESA_LOGGING_LEVEL=DEBUG    -> cfg["logging"]["level"] = "DEBUG"
      - TESA_ARCHIMEDEAN_EPSILON_PARAMS_C_EPSILON=0.5
      - TESA_SPECTRAL_CLIP_EPS=1e-10
      - TESA_PATHS_OUTPUTS_DIR="my_out"
    Regras:
      - Nome após prefixo é separado por '_' e mapeado para chaves minúsculas,
        exceto números que permanecem números de índice (não aplicamos aqui).
      - Usa navegação/ criação de dicionários se necessário.
    """
    plen = len(prefix)
    for env_k, env_v in os.environ.items():
        if not env_k.startswith(prefix):
            continue
        path_keys = env_k[plen:].split("_")
        # caminho de chaves em minúsculas
        keys = [k.lower() for k in path_keys if k]
        if not keys:
            continue
        # navegar/criar
        cur = cfg
        for k in keys[:-1]:
            if k not in cur or not isinstance(cur[k], dict):
                cur[k] = {}
            cur = cur[k]
        leaf = keys[-1]
        cur[leaf] = _parse_env_value(env_v)
    return cfg


def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validação leve: corrige tipos e aplica limites simples.
    """
    # logging.level
    lvl = str(cfg.get("logging", {}).get("level", "INFO")).upper()
    if lvl not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        cfg["logging"]["level"] = "INFO"
    else:
        cfg["logging"]["level"] = lvl

    # orchestrator.max_workers: inteiro >=1
    try:
        mw = int(cfg.get("orchestrator", {}).get("max_workers", 1))
        if mw < 1:
            mw = 1
        cfg["orchestrator"]["max_workers"] = mw
    except Exception:
        cfg["orchestrator"]["max_workers"] = 1

    # spectral.clip_eps: float pequeno positivo
    try:
        ce = float(cfg.get("spectral", {}).get("clip_eps", 1e-12))
        if not (0.0 < ce < 1e-1):
            ce = 1e-12
        cfg["spectral"]["clip_eps"] = ce
    except Exception:
        cfg["spectral"]["clip_eps"] = 1e-12

    # archimedean.mean_atol: float positivo
    try:
        atol = float(cfg.get("archimedean", {}).get("mean_atol", 1e-9))
        if atol <= 0:
            atol = 1e-9
        cfg["archimedean"]["mean_atol"] = atol
    except Exception:
        cfg["archimedean"]["mean_atol"] = 1e-9

    # archimedean.epsilon_params.C_epsilon
    try:
        ceps = float(cfg["archimedean"]["epsilon_params"].get("C_epsilon", 1.0))
        if ceps < 0:
            ceps = 0.0
        cfg["archimedean"]["epsilon_params"]["C_epsilon"] = ceps
    except Exception:
        cfg["archimedean"]["epsilon_params"]["C_epsilon"] = 1.0

    # booleans coerção segura
    def to_bool(x: Any, default: bool) -> bool:
        if isinstance(x, bool):
            return x
        if isinstance(x, str):
            return x.strip().lower() in ("1", "true", "yes", "on")
        if isinstance(x, (int, float)):
            return bool(x)
        return default

    cfg["logging"]["to_console"] = to_bool(cfg["logging"].get("to_console", True), True)
    cfg["logging"]["to_file"] = to_bool(cfg["logging"].get("to_file", False), False)
    cfg["io"]["csv_export"] = to_bool(cfg["io"].get("csv_export", True), True)
    cfg["io"]["png_plot"] = to_bool(cfg["io"].get("png_plot", True), True)

    return cfg


def load_config(
    json_path: Optional[str] = None,
    env_prefix: str = "TESA_",
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Carrega a configuração completa com a seguinte ordem de precedência:
      1) DEFAULT_CONFIG
      2) Conteúdo de json_path (se fornecido)
      3) Overrides via argumento 'overrides' (dict)
      4) Variáveis de ambiente (prefixo env_prefix)
    Em seguida, valida e retorna.
    """
    cfg = get_default_config()

    if json_path:
        cfg_json = load_config_json(json_path)
        if cfg_json:
            deep_update(cfg, cfg_json)

    if overrides:
        deep_update(cfg, overrides)

    apply_env_overrides(cfg, prefix=env_prefix)

    return validate_config(cfg)


# Helper de impressão segura (debug)
def pretty(cfg: Dict[str, Any]) -> str:
    """
    Retorna uma string JSON bonita e estável para inspeção.
    """
    try:
        return json.dumps(cfg, indent=2, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(cfg)
