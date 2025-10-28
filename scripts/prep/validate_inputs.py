import json
from pathlib import Path

import yaml
from jsonschema import Draft7Validator, exceptions as jsonschema_exceptions

from scripts.common.io_utils import read_json, read_yaml, list_files


SCHEMAS_DIR = Path("tesa-machine/schemas")
DATA_DIR = Path("tesa-machine/data")


def _load_schema(schema_name: str):
    """
    Carrega um schema JSON do diretório de schemas.
    """
    schema_path = SCHEMAS_DIR / schema_name
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema não encontrado: {schema_path}")
    try:
        return read_json(schema_path)
    except json.JSONDecodeError as e:
        raise ValueError(f"Schema inválido ({schema_path}): {e}")


def _validate_with_schema(instance, schema, context_label=""):
    """
    Valida um objeto contra um schema JSON. Retorna lista de erros (strings).
    """
    validator = Draft7Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(instance), key=lambda e: e.path):
        loc = ".".join([str(p) for p in error.path]) if error.path else "(root)"
        errors.append(f"[{context_label}] {loc}: {error.message}")
    return errors


def validate_types():
    """
    Valida o arquivo YAML de tipos (E_n/D_n) contra o schema correspondente.
    """
    schema = _load_schema("type_schema.json")
    types_path = DATA_DIR / "types" / "En_Dn_library.yaml"
    if not types_path.exists():
        raise FileNotFoundError(f"Arquivo de tipos não encontrado: {types_path}")
    try:
        types_data = read_yaml(types_path)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML de tipos inválido ({types_path}): {e}")

    errors = _validate_with_schema(types_data, schema, context_label="types")
    return errors


def validate_metrics():
    """
    Valida o catálogo de métricas contra o schema correspondente.
    """
    schema = _load_schema("metric_schema.json")
    metrics_path = DATA_DIR / "metrics" / "metrics_catalog.yaml"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Arquivo de métricas não encontrado: {metrics_path}")
    try:
        metrics_data = read_yaml(metrics_path)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML de métricas inválido ({metrics_path}): {e}")

    errors = _validate_with_schema(metrics_data, schema, context_label="metrics")
    return errors


def validate_all():
    """
    Executa todas as validações e retorna um relatório.
    """
    report = {
        "types": {"errors": []},
        "metrics": {"errors": []},
    }

    report["types"]["errors"] = validate_types()
    report["metrics"]["errors"] = validate_metrics()

    report["ok"] = len(report["types"]["errors"]) == 0 and len(report["metrics"]["errors"]) == 0
    return report


def print_report(report: dict):
    """
    Imprime o relatório de validação de forma amigável.
    """
    print("=== Validação de entradas ===")
    for section in ("types", "metrics"):
        errs = report[section]["errors"]
        if errs:
            print(f"- {section}: {len(errs)} erro(s)")
            for e in errs:
                print(f"  * {e}")
        else:
            print(f"- {section}: OK")
    print(f"Resultado geral: {'OK' if report.get('ok') else 'FALHOU'}")


if __name__ == "__main__":
    try:
        rpt = validate_all()
        print_report(rpt)
    except (FileNotFoundError, ValueError, jsonschema_exceptions.SchemaError) as e:
        print(f"Erro de validação: {e}")