Metadados do pacote
title = "tesa"
version = "0.1.0"
author = "Paulo Vieira"
license = "MIT"
description = "Máquina TESA: Identidade Global TESA, soma Arakeloviana e módulos locais/arquimedianos."

Exportações públicas do subpacote tesa
from .local_c_type import (
KV_TABLE,
FV_TAME,
get_graph,
compute_C_type_for_graph,
run_all_tests,
export_results_csv,
plot_bar_by_i0,
plot_fv_by_type,
plot_graph_with_values,
plot_edge_currents,
)

from .global_orchestrator import (
run_tesa_pipeline,
assemble_global_constant,
tesa_global_bound,
)

from .spectral import compute_delta
from .archimedean import compute_C_infty

from .io_report import (
export_local_summary_csv,
export_global_summary_csv,
plot_Ctype_by_place,
plot_bound_comparison,
)

from .config import load_family_config

Controle de exportações com all
all = [
# Metadados não entram em all
# local_c_type
"KV_TABLE",
"FV_TAME",
"get_graph",
"compute_C_type_for_graph",
"run_all_tests",
"export_results_csv",
"plot_bar_by_i0",
"plot_fv_by_type",
"plot_graph_with_values",
"plot_edge_currents",
# global_orchestrator
"run_tesa_pipeline",
"assemble_global_constant",
"tesa_global_bound",
# spectral
"compute_delta",
# archimedean
"compute_C_infty",
# io_report
"export_local_summary_csv",
"export_global_summary_csv",
"plot_Ctype_by_place",
"plot_bound_comparison",
# config
"load_family_config",
]
