import argparse
from pathlib import Path
import sys

from scripts.prep.validate_inputs import validate_all, print_report
from scripts.prep.build_graphs import build_all
from scripts.metrics.evaluate_metrics import evaluate_all
from scripts.common.io_utils import ensure_dir, write_json, write_yaml, read_json, read_yaml


BUILD_DIR = Path("tesa-machine/build")


def cmd_validate(args):
    rpt = validate_all()
    print_report(rpt)
    # opcionalmente salvar relatório
    if args.output:
        out_path = Path(args.output)
        ensure_dir(out_path.parent)
        if out_path.suffix.lower() == ".json":
            write_json(out_path, rpt, indent=2)
        elif out_path.suffix.lower() in (".yml", ".yaml"):
            write_yaml(out_path, rpt)
        else:
            # padrão: json
            write_json(out_path.with_suffix(".json"), rpt, indent=2)


def cmd_build_graphs(args):
    index = build_all(save_formats=tuple(args.format))
    print(f"Construídos {len(index)} grafo(s).")
    # salva índice adicional se solicitado
    if args.output:
        out_path = Path(args.output)
        ensure_dir(out_path.parent)
        payload = {"graphs": index}
        if out_path.suffix.lower() == ".json":
            write_json(out_path, payload, indent=2)
        elif out_path.suffix.lower() in (".yml", ".yaml"):
            write_yaml(out_path, payload)
        else:
            write_json(out_path.with_suffix(".json"), payload, indent=2)


def cmd_eval_metrics(args):
    selected = args.metrics if args.metrics else None
    out = evaluate_all(selected_metrics=selected)
    print(f"Avaliações concluídas para {len(out['results'])} entrada(s).")
    # salva índice adicional se solicitado
    if args.output:
        out_path = Path(args.output)
        ensure_dir(out_path.parent)
        if out_path.suffix.lower() == ".json":
            write_json(out_path, out, indent=2)
        elif out_path.suffix.lower() in (".yml", ".yaml"):
            write_yaml(out_path, out)
        else:
            write_json(out_path.with_suffix(".json"), out, indent=2)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="tesa-machine",
        description="CLI para preparação de dados e avaliação de métricas da TESA Machine."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # validate
    p_val = sub.add_parser("validate", help="Valida entradas (types e metrics) contra schemas.")
    p_val.add_argument("-o", "--output", help="Caminho para salvar relatório (json/yaml).", default=None)
    p_val.set_defaults(func=cmd_validate)

    # build-graphs
    p_build = sub.add_parser("build-graphs", help="Constrói grafos a partir da biblioteca En_Dn.")
    p_build.add_argument(
        "-f", "--format",
        nargs="+",
        choices=["json", "yaml"],
        default=["json", "yaml"],
        help="Formato(s) de saída dos grafos."
    )
    p_build.add_argument("-o", "--output", help="Caminho para salvar índice adicional.", default=None)
    p_build.set_defaults(func=cmd_build_graphs)

    # eval-metrics
    p_eval = sub.add_parser("eval-metrics", help="Avalia métricas definidas no catálogo para todos os grafos.")
    p_eval.add_argument(
        "-m", "--metrics",
        nargs="+",
        help="Lista de métricas a executar (por nome). Se omitido, executa todas disponíveis."
    )
    p_eval.add_argument("-o", "--output", help="Caminho para salvar índice adicional.", default=None)
    p_eval.set_defaults(func=cmd_eval_metrics)

    return parser


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()