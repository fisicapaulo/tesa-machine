# run_g1_example.py
# Uso no Colab:
# - Certifique-se de ter a estrutura e módulos tesa instalados no path atual.
# - Este script lê config/family.yaml, roda o pipeline g=1 e gera relatórios/plots em outputs/.
import os
from tesa.config import load_family_config
from tesa.local_c_type import get_graph, compute_C_type_for_graph, KV_TABLE
from tesa.global_orchestrator import run_tesa_pipeline, tesa_global_bound
from tesa.spectral import compute_delta
from tesa.archimedean import compute_C_infty
from tesa.io_report import export_local_summary_csv, export_global_summary_csv, plot_Ctype_by_place, plot_bound_comparison

def main():
    cfg = load_family_config("config/family.yaml")
    family = cfg["g1_example"]
    places = family["places"]

    local_results = []
    for v in places:
        gcode = v["graph"]
        edges, n, name = get_graph(gcode)
        Kv = KV_TABLE.get(v.get("p"), {}).get(name, 0.0)
        i0 = int(v.get("i0", 0))
        c = float(v.get("conductance", 1.0))
        res = compute_C_type_for_graph(
            edges=edges, n=n, name=name, i0=i0, K_v=Kv, conductance=c,
            weights=None, ref_index=0, check=True
        )
        res["place"] = v["place"]
        local_results.append(res)

    info = run_tesa_pipeline(
        g=1,
        family_data={"delta_lower_bound": family.get("delta_lower_bound", 0.03)},
        local_results=local_results,
        L_data={"bundle": "Neron-Tate"},
        metric_data={"mean_zero": True},
        epsilon_params=family.get("epsilon_params", {"C_epsilon": 1.0}),
        delta_computer=compute_delta,
        arch_computer=compute_C_infty,
        err_locals_sum=float(family.get("err_locals_sum", 0.0)),
    )

    os.makedirs("outputs", exist_ok=True)
    path_loc = export_local_summary_csv(local_results, out_dir="outputs", base_name="g1_locals")
    paths_global = export_global_summary_csv(info, out_dir="outputs", base_name="g1_global")
    plot_Ctype_by_place(local_results, title="g=1 — C_Type por lugar", out_dir="outputs", fname="g1_Ctype.png")

    # Comparação h vs RHS (exemplo sintético por lugar listado)
    samples = []
    for k, v in enumerate(places):
        hL = float(places[k].get("h_sample", 3.0 + k))
        mD = float(places[k].get("mD_sample", 4.0 + 0.5 * k))
        RHS = tesa_global_bound(hL, mD, info["delta"], info["C_global"])
        samples.append({"label": v["place"], "h_L": hL, "RHS": RHS})
    plot_bound_comparison(samples, title="g=1 — h vs RHS", out_dir="outputs", fname="g1_bound.png")

    print("OK g=1")
    print("Locais CSV:", path_loc)
    print("Global CSV e certificados:", paths_global)

if __name__ == "__main__":
    main()
