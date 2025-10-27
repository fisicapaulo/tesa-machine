# TESA-MACHINE — Máquina da Identidade Global TESA

## Visão geral
Este repositório implementa a Máquina TESA em quatro módulos principais:
1. Espectral (delta): obtém um ganho de coerção uniforme δ (Axioma 2).
2. Local C_Type: agrega constantes locais C_Type,v (K_v + E_Fenchel) a partir de grafos de redução.
3. Arquimediano (C_∞): calibra a constante contínua sob métrica admissível com média zero.
4. Soma Global: compõe C_Global e avalia a desigualdade
   h_L(P) ≤ (1 − δ) m_D(P) + C_Global.

## Estrutura do repositório
```
tesa-machine/
  tesa/
    __init__.py
    local_c_type.py
    global_orchestrator.py
    archimedean.py
    spectral.py
    io_report.py
    config.py
  examples/
    run_g1_example.py
    run_gge2_example.py
  config/
    family.yaml
  outputs/            (gerado em runtime)
  README.md           (este arquivo)
```

## Instalação
Requisitos: Python 3.9+ e pacotes:
- numpy
- scipy
- matplotlib
- pyyaml

Instalação (Colab ou local):
```bash
pip install numpy scipy matplotlib pyyaml
```

## Como rodar os exemplos

### 1) Exemplo g = 1 (curvas elípticas)
- Ajuste os lugares em `config/family.yaml` (se necessário).
- Execute:
  ```bash
  python examples/run_g1_example.py
  ```
- Saídas geradas:
  - `outputs/g1_locals_summary.csv` — resumo locais (C_Type,v)
  - `outputs/g1_global_summary.csv` — resumo global (δ, Σ C_Type, C_∞, C_Global)
  - `outputs/g1_global_certificates.txt` — certificados/relatórios
  - `outputs/g1_Ctype.png` — barras: C_Type por lugar
  - `outputs/g1_bound.png` — comparação h vs RHS

### 2) Exemplo g ≥ 2 (curvas de gênero ≥ 2 / fibras estáveis)
- Ajuste os lugares em `config/family.yaml` (se necessário).
- Execute:
  ```bash
  python examples/run_gge2_example.py
  ```
- Saídas geradas:
  - `outputs/gge2_locals_summary.csv`
  - `outputs/gge2_global_summary.csv`
  - `outputs/gge2_global_certificates.txt`
  - `outputs/gge2_Ctype.png`
  - `outputs/gge2_bound.png`

## Componentes principais

### tesa/local_c_type.py
- Tabelas K_v (`KV_TABLE`) e f_v^tame (`FV_TAME`).
- Construção de grafos (E6/E7/E8, Dn, etc.).
- Solver de potenciais/correntes e energia de Fenchel.
- `compute_C_type_for_graph(...)`: retorna C_Type,v por lugar.
- Funções utilitárias de teste e plots.

### tesa/spectral.py
- `compute_delta(g, family_data)`: placeholder do Axioma 2, retornando δ com certificado.
- Substituir por rotina espectral certificada (autovalor mínimo/lacuna).

### tesa/archimedean.py
- `compute_C_infty(L_data, metric_data, epsilon_params)`: placeholder para C_∞.
- Integra normalização de média zero e bound L∞ do potencial contínuo.

### tesa/global_orchestrator.py
- `run_tesa_pipeline(...)`: compõe δ, Σ C_Type, C_∞ e retorna C_Global com relatórios.
- `tesa_global_bound(h_L, m_D, δ, C_Global)`: avalia o lado direito da desigualdade TESA.

### tesa/io_report.py
- `export_local_summary_csv(...)`, `export_global_summary_csv(...)`
- `plot_Ctype_by_place(...)`, `plot_bound_comparison(...)`

### tesa/config.py
- `load_family_config(path)`: carrega `config/family.yaml`.

### config/family.yaml
- Define dois cenários: `g1_example` e `gge2_example`, com lista de lugares, tipos, p, i0, condutâncias, parâmetros arquimedianos e `delta_lower_bound`.

## Notas técnicas e próximos passos

### Espectral (δ)
- Substituir placeholder por certificador de gap espectral (ex.: autovalor mínimo de operadores discretos/globais por lugar e inf_v).
- Emitir certificado com intervalos verificados (ex.: aritmética intervalar).

### Arquimediano (C_∞)
- Implementar cálculo do potencial de Green contínuo sob métrica admissível de média zero.
- Controlar sup-norm do potencial e normalização (∫ potencial = 0).

### Locais (C_Type,v)
- Expandir `KV_TABLE` e `FV_TAME` para mais primos/tipos.
- Incluir pesos/multiplicidades das componentes se necessário.

### Validação empírica
- Conectar exemplos g=1 a curvas elípticas reais (modelo minimal, tipos de Kodaira).
- Para g≥2, usar grafos reais de redução estável (dual graphs) e comparar com benchmarks.

## Suporte e licença
- Use Issues e Pull Requests para discutir melhorias e reportar problemas.
- Licença: MIT

## Créditos e motivação
Este repositório consolida a Máquina TESA, integrando módulos locais/globais com auditoria de constantes e relatórios automatizados. O objetivo é oferecer uma base reprodutível e extensível para validações das formas de Vojta/Lang, Szpiro/ABC e aplicações relacionadas em Arakelov e teoria de alturas.
