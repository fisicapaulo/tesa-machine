# =============================================================================
# tesa.local_c_type
#
# Propósito:
# - Definir grafos locais (tipos D4/D5/D6/E6/E7/E8) e utilitários associados.
# - Calcular quantidades locais: f_v^tame, f_v, energia de Fenchel discreta
#   e o valor C_type para um grafo local dado (place v).
# - Fornecer utilidades para exportação (CSV) e visualização (plots).
#
# Observações de projeto:
# - As fórmulas usadas para f_v, energia e C_type são placeholders simples,
#   visando transparência e facilidade de substituição. Quando a formulação
#   final estiver definida, ajuste as funções f_v, fenchel_energy e
#   compute_C_type_for_graph.
# - Os grafos D/E aqui são modelos sintéticos (Dynkin-like) para experimentação.
#   Substitua por grafos/estruturas oficiais quando necessário.
#
# Dependências (runtime):
# - networkx (distâncias em grafos e layout para plots)
# - matplotlib (plots)
# - csv (exportação de resultados)
# - math (verificações e operações básicas)
#
# Uso típico:
#   edges, n, name = get_graph("E6")
#   Kv = KV_TABLE.get(2, {}).get(name, 0.0)
#   res = compute_C_type_for_graph(edges, n, name, i0=3, K_v=Kv, conductance=1.0)
#   export_results_csv([res], "outputs/local_results.csv")
#
# Notas:
# - A tabela KV_TABLE e o dicionário FV_TAME são parâmetros ajustáveis.
# - Para rodar os plots, instale as dependências e garanta que a pasta
#   "outputs/" exista (ou ajuste os caminhos out_path nas funções de plot).
# - Este módulo pode ser executado diretamente (python local_c_type.py)
#   para uma demonstração rápida e geração de figuras.
#
# Licença:
# - MIT 
# =============================================================================
import math
import csv
from typing import List, Tuple, Dict, Any, Optional

# Imports opcionais para plot
import matplotlib.pyplot as plt
import networkx as nx

# ============================================================
# Tabela KV: penalidades locais por primo p e tipo (placeholder)
# Você pode ajustar posteriormente conforme sua teoria/cálculo.
# ============================================================
KV_TABLE: Dict[int, Dict[str, float]] = {
    2: {"D4": 0.15, "D5": 0.18, "D6": 0.20, "E6": 0.22, "E7": 0.25, "E8": 0.28},
    3: {"D4": 0.10, "D5": 0.12, "D6": 0.14, "E6": 0.16, "E7": 0.18, "E8": 0.20},
    5: {"D4": 0.00, "D5": 0.00, "D6": 0.00, "E6": 0.00, "E7": 0.00, "E8": 0.00},
    7: {"D4": 0.00, "D5": 0.00, "D6": 0.00, "E6": 0.00, "E7": 0.00, "E8": 0.00},
}

# ============================================================
# Definições de grafos sintéticos por tipo (Dynkin-like)
# Cada grafo é uma lista de arestas (u, v) não orientadas e
# o número de nós n.
# ============================================================
def graph_D4() -> Tuple[List[Tuple[int, int]], int, str]:
    # Estrela com 4 folhas: 0-1, 0-2, 0-3, 0-4
    edges = [(0,1),(0,2),(0,3),(0,4)]
    n = 5
    return edges, n, "D4"

def graph_D5() -> Tuple[List[Tuple[int, int]], int, str]:
    # D5: estrela 0-1,0-2,0-3 e rabo 0-4-5
    edges = [(0,1),(0,2),(0,3),(0,4),(4,5)]
    n = 6
    return edges, n, "D5"

def graph_D6() -> Tuple[List[Tuple[int, int]], int, str]:
    # D6: estrela 0-1,0-2,0-3 e rabo 0-4-5-6
    edges = [(0,1),(0,2),(0,3),(0,4),(4,5),(5,6)]
    n = 7
    return edges, n, "D6"

def graph_E6() -> Tuple[List[Tuple[int, int]], int, str]:
    # E6 simplificado: cadeia 0-1-2-3-4 e ramificação em 2-5
    edges = [(0,1),(1,2),(2,3),(3,4),(2,5)]
    n = 6
    return edges, n, "E6"

def graph_E7() -> Tuple[List[Tuple[int, int]], int, str]:
    # E7 simplificado: cadeia 0-1-2-3-4-5 e ramificação em 3-6
    edges = [(0,1),(1,2),(2,3),(3,4),(4,5),(3,6)]
    n = 7
    return edges, n, "E7"

def graph_E8() -> Tuple[List[Tuple[int, int]], int, str]:
    # E8 simplificado: cadeia 0-1-2-3-4-5-6 e ramificação em 2-7
    edges = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(2,7)]
    n = 8
    return edges, n, "E8"

# Mapeamento de código textual para o grafo
def get_graph(code: str) -> Tuple[List[Tuple[int, int]], int, str]:
    code = code.upper().strip()
    if code == "D4":
        return graph_D4()
    if code == "D5":
        return graph_D5()
    if code == "D6":
        return graph_D6()
    if code == "E6":
        return graph_E6()
    if code == "E7":
        return graph_E7()
    if code == "E8":
        return graph_E8()
    raise ValueError(f"Tipo de grafo desconhecido: {code}")

# ============================================================
# f_v^tame e f_v (placeholder)
# FV_TAME retorna o peso "tame" base associado ao tipo,
# que será usado em f_v. Você pode calibrar depois.
# ============================================================
FV_TAME: Dict[str, float] = {
    "D4": 0.80,
    "D5": 0.85,
    "D6": 0.90,
    "E6": 0.95,
    "E7": 1.00,
    "E8": 1.05,
}

def f_v_tame(name: str) -> float:
    return float(FV_TAME.get(name, 1.0))

def f_v(name: str, K_v: float, conductance: float = 1.0) -> float:
    """
    f_v = f_v^tame + ajuste(K_v, c)
    Ajuste simples: f_v = f_v^tame * (1 + K_v) / max(c, 1e-9)
    """
    base = f_v_tame(name)
    c = max(float(conductance), 1e-9)
    return base * (1.0 + float(K_v)) / c

# ============================================================
# Energia de Fenchel discreta em um grafo
# Consideramos um potencial φ nos nós (com referência φ[ref]=0)
# e correntes nas arestas J = c*(φ_u - φ_v). A energia:
# E = 0.5 * sum_{(u,v)} c * (φ_u - φ_v)^2
# ============================================================
def fenchel_energy(edges: List[Tuple[int,int]], phi: List[float], conductance: float = 1.0) -> float:
    c = float(conductance)
    e = 0.0
    for (u, v) in edges:
        e += 0.5 * c * (phi[u] - phi[v])**2
    return float(e)

# ============================================================
# Construção de potencial φ com base em i0, f_v, e posição de referência
# - i0: parâmetro inteiro que determina a queda de potencial
# - ref_index: nó onde φ = 0 (fixação de gauge)
# A política aqui é simples: φ[k] = (i0 - dist(k, ref)) * scale
# com scale proporcional a f_v.
# ============================================================
def shortest_path_distances(n: int, edges: List[Tuple[int,int]], ref_index: int = 0) -> List[int]:
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from(edges)
    d = []
    for k in range(n):
        try:
            d.append(nx.shortest_path_length(G, source=ref_index, target=k))
        except nx.NetworkXNoPath:
            d.append(10**6)
    return d

def build_potential(
    n: int,
    edges: List[Tuple[int,int]],
    i0: int,
    f_v_value: float,
    ref_index: int = 0
) -> List[float]:
    dists = shortest_path_distances(n, edges, ref_index=ref_index)
    scale = max(f_v_value, 1e-9)
    phi = []
    for k in range(n):
        phi_k = (float(i0) - float(dists[k])) * scale
        # Não permitir valores extremamente negativos para nós desconectados
        if dists[k] >= 10**5:
            phi_k = 0.0
        phi.append(phi_k)
    return phi

# ============================================================
# Cálculo de C_Type para um grafo local:
# retorna dict com: name, n, i0, K_v, f_v_tame, f_v, E_fenchel, C_type
# ============================================================
def compute_C_type_for_graph(
    edges: List[Tuple[int,int]],
    n: int,
    name: str,
    i0: int,
    K_v: float,
    conductance: float = 1.0,
    weights: Optional[List[float]] = None,
    ref_index: int = 0,
    check: bool = True
) -> Dict[str, Any]:
    # f_v e potencial
    fv_tame = f_v_tame(name)
    fv = f_v(name, K_v=K_v, conductance=conductance)

    phi = build_potential(n, edges, i0=i0, f_v_value=fv, ref_index=ref_index)
    E = fenchel_energy(edges, phi, conductance=conductance)

    # C_Type,v := E + K_v (placeholder; pode ser outra função)
    C_type = float(E + K_v)

    # Verificação simples
    if check:
        assert n >= 1 and len(edges) >= 1, "Grafo deve ter pelo menos 1 aresta."
        assert math.isfinite(E), "Energia não finita."
        assert math.isfinite(C_type), "C_type não finito."

    return {
        "name": name,
        "n": n,
        "i0": int(i0),
        "K_v": float(K_v),
        "conductance": float(conductance),
        "f_v_tame": float(fv_tame),
        "f_v": float(fv),
        "E_fenchel": float(E),
        "C_type": float(C_type),
    }

# ============================================================
# Exportação CSV básica de resultados locais
# ============================================================
def export_results_csv(results: List[Dict[str, Any]], path: str) -> str:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name","n","i0","K_v","conductance","f_v^tame","f_v","E_fenchel","C_Type"])
        for r in results:
            w.writerow([
                r["name"], r["n"], r["i0"], r["K_v"], r["conductance"],
                r["f_v_tame"], r["f_v"], r["E_fenchel"], r["C_type"]
            ])
    return path

# ============================================================
# Plots utilitários
# ============================================================
def plot_bar_by_i0(results: List[Dict[str, Any]], title: str = "C_Type por i0", out_path: str = "outputs/plot_bar_by_i0.png"):
    xs = [r["i0"] for r in results]
    ys = [r["C_type"] for r in results]
    fig, ax = plt.subplots(figsize=(6.5,3.5))
    ax.bar(xs, ys, color="#4C72B0")
    ax.set_xlabel("i0")
    ax.set_ylabel("C_Type")
    ax.set_title(title)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path

def plot_fv_by_type(results: List[Dict[str, Any]], title: str = "f_v por tipo", out_path: str = "outputs/plot_fv_by_type.png"):
    xs = [r["name"] for r in results]
    ys = [r["f_v"] for r in results]
    fig, ax = plt.subplots(figsize=(6.5,3.5))
    ax.bar(xs, ys, color="#1B9E77")
    ax.set_xlabel("Tipo")
    ax.set_ylabel("f_v")
    ax.set_title(title)
    ax.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=20, ha='right')
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path

def plot_graph_with_values(edges: List[Tuple[int,int]], values: List[float], title: str = "Grafo e φ", out_path: str = "outputs/plot_graph.png"):
    G = nx.Graph()
    n = len(values)
    G.add_nodes_from(range(n))
    G.add_edges_from(edges)
    pos = nx.spring_layout(G, seed=7)
    fig, ax = plt.subplots(figsize=(6.5,4.5))
    nx.draw(G, pos, with_labels=True, node_color="#E0E0E0", edge_color="#888888", node_size=600, ax=ax)
    labels = {i: f"{i}\n{values[i]:.2f}" for i in range(n)}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, ax=ax)
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path

def plot_edge_currents(edges: List[Tuple[int,int]], phi: List[float], conductance: float = 1.0, title: str = "Correntes nas arestas", out_path: str = "outputs/plot_edge_currents.png"):
    G = nx.Graph()
    n = len(phi)
    G.add_nodes_from(range(n))
    G.add_edges_from(edges)
    pos = nx.spring_layout(G, seed=5)
    fig, ax = plt.subplots(figsize=(6.5,4.5))
    nx.draw(G, pos, with_labels=True, node_color="#FAFAFA", edge_color="#999999", node_size=650, ax=ax)
    # Corrente J = c*(φ_u - φ_v)
    c = float(conductance)
    widths = []
    for (u, v) in edges:
        j = abs(c * (phi[u] - phi[v]))
        widths.append(1.0 + 2.0 * j)  # espessura proporcional à corrente
    # Desenhar novamente com espessuras
    nx.draw_networkx_edges(G, pos, edgelist=edges, width=widths, edge_color="#3778C2", ax=ax)
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path

# ============================================================
# Testes simples locais
# ============================================================
def run_all_tests() -> List[Dict[str, Any]]:
    tests = []
    for maker in [graph_D4, graph_D5, graph_D6, graph_E6, graph_E7, graph_E8]:
        edges, n, name = maker()
        res = compute_C_type_for_graph(edges, n, name, i0=3, K_v=KV_TABLE.get(2, {}).get(name, 0.0), conductance=1.0)
        tests.append(res)
    return tests

# ============================================================
# Pequeno bloco de demonstração ao rodar isoladamente
# (Opcional: você pode remover se quiser)
# ============================================================
if __name__ == "__main__":
    # Demonstração rápida
    edges, n, name = graph_E6()
    Kv = KV_TABLE.get(2, {}).get(name, 0.0)
    res = compute_C_type_for_graph(edges, n, name, i0=3, K_v=Kv, conductance=1.0)
    print("Resultado local:", res)
    # Plots
    phi = build_potential(n, edges, i0=3, f_v_value=res["f_v"], ref_index=0)
    plot_graph_with_values(edges, phi, title=f"Grafo {name} — φ", out_path="outputs/demo_graph_phi.png")
    plot_edge_currents(edges, phi, conductance=1.0, title=f"Grafo {name} — correntes", out_path="outputs/demo_edge_currents.png")
