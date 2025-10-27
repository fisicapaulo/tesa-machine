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

- Seções sugeridas para adicionar ao final do README.md:

Se preferir, substitua os campos entre colchetes.

— INÍCIO DO BLOCO COPIAR/ COLAR —

## Limitações atuais

Este repositório está em desenvolvimento ativo e contém componentes com aproximações controladas:

- Módulo espectral (δ): o arquivo `tesa/spectral.py` usa um placeholder para fornecer um lower bound para δ (Axioma 2). A futura versão certificada deverá calcular lacunas espectrais com verificação (p.ex., autovalores mínimos com aritmética intervalar).
- Componente arquimediano (C_∞): o arquivo `tesa/archimedean.py` utiliza uma aproximação para o potencial contínuo sob métrica admissível com normalização de média zero. Em versões futuras, pretendemos implementar integração numérica certificada (com controle de erro e bounds verificados).
- Configurações de exemplo: os cenários em `config/family.yaml` são ilustrativos. Para uso em pesquisa, ajuste cuidadosamente os parâmetros (lugares, tipos, condutâncias) de acordo com o caso estudado e documente as escolhas no relatório/outputs.
- Estabilidade numérica: rotinas de resolução linear e cálculo de energias (Fenchel, potenciais, etc.) podem ser sensíveis ao condicionamento. Recomendamos verificar tolerâncias, checar condicionamentos das matrizes envolvidas e, quando necessário, ativar logs detalhados para auditoria.

## Reprodutibilidade

Para reforçar a reprodutibilidade dos resultados:

- Versões de dependências: utilize o `requirements.txt` fornecido. Versões mínimas sugeridas:
  - numpy>=1.22
  - scipy>=1.8
  - matplotlib>=3.5
  - pyyaml>=6.0
  - networkx>=2.8
- Ambiente: recomendamos Python 3.9+ e execução em ambiente virtual (venv ou conda).
- Saídas determinísticas: scripts em `examples/` criam a pasta `outputs/` (se necessário) e gravam relatórios e gráficos. Inclua nos relatórios o commit hash do Git, timestamp e versões de bibliotecas (ver seção “Certificados e auditoria”).
- Versionamento: use tags (por exemplo, `v0.1.0`) para fixar o estado do código citado em artigos.

## Certificados e auditoria

Os relatórios gerados (por exemplo, `*_global_certificates.txt`) devem registrar:

- Carimbo de data/hora da execução
- Commit hash do repositório (se disponível)
- Versões de Python e bibliotecas (numpy, scipy, matplotlib, pyyaml, networkx)
- Cenário e parâmetros efetivos (oriundos de `config/family.yaml`)
- Resumo das constantes: δ, soma de C_Type,v, C_∞, C_Global
- Verificações/checs básicos (ex.: não negatividade, coerência de limites inferiores/superiores)

Isso facilita a validação independente e a citação reprodutível.

## Como citar

Se este repositório for útil em sua pesquisa, por favor cite:

- Citação em texto: “Máquina TESA (tesa-machine), versão [vX.Y.Z], [autor/es], [ano].”
- BibTeX (exemplo):

@software{tesa_machine_[ANO],
  author  = {Paulo Vieira},
  title   = {TESA-MACHINE — Máquina da Identidade Global TESA},
  year    = {2025},
  version = {v0.1.0},
  url     = {https://github.com/fisicapaulo/tesa-machine},
  license = {MIT}
}

## Roadmap (curto prazo)

- Substituir o placeholder espectral por rotina certificada de lacuna espectral (com aritmética intervalar e certificados numéricos).
- Implementar cálculo arquimediano C_∞ com integração verificada e controle de erro.
- Ampliar casos de teste (g=1 e g≥2) com exemplos reais, incluindo comparações com literatura.
- Adicionar testes automatizados (pytest) e CI (GitHub Actions) para validar exemplos.
- Enriquecer os relatórios com métricas de condicionamento e tolerâncias usadas nos solvers.

## Suporte e contribuições

- Issues: use a aba “Issues” do GitHub para reportar bugs, propor melhorias ou discutir casos específicos.
- Pull requests: contribuições são bem-vindas. Por favor, inclua testes e atualize a documentação quando necessário.
- Licença: este projeto é distribuído sob a licença MIT (ver arquivo LICENSE).

## Suporte e licença
- Use Issues e Pull Requests para discutir melhorias e reportar problemas.
- Licença: MIT

## Créditos e motivação
Este repositório consolida a Máquina TESA, integrando módulos locais/globais com auditoria de constantes e relatórios automatizados. O objetivo é oferecer uma base reprodutível e extensível para validações das formas de Vojta/Lang, Szpiro/ABC e aplicações relacionadas em Arakelov e teoria de alturas.
