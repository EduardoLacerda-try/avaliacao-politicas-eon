# Avaliação de Políticas de Alocação Espectral em Redes Ópticas Elásticas

Este repositório contém o simulador desenvolvido para o Trabalho de Conclusão de Curso intitulado **"Avaliação de Políticas de Alocação Espectral em Redes Ópticas Elásticas com Tráfego Multiclasse"**.

O objetivo do simulador é comparar políticas de alocação espectral em Redes Ópticas Elásticas (*Elastic Optical Networks - EONs*), considerando tráfego dinâmico multiclasse e restrições de contiguidade, continuidade e não sobreposição de slots.

## Sobre o projeto

As Redes Ópticas Elásticas permitem a alocação flexível do espectro óptico em blocos de slots, ajustados à demanda de cada conexão. Entretanto, essa flexibilidade introduz desafios relacionados ao roteamento, à alocação de espectro, à fragmentação espectral e ao desalinhamento dos blocos disponíveis ao longo das rotas.

Neste projeto, foi desenvolvido um simulador de eventos discretos em Python para avaliar o comportamento de uma EON sob diferentes composições de tráfego e intensidades de carga. O foco principal está na comparação entre duas combinações de políticas de alocação espectral:

- **FF/FF**: requisições small e large alocadas com First-Fit;
- **FF/LF**: requisições small alocadas com First-Fit e requisições large alocadas com Last-Fit.

Além da probabilidade de bloqueio total, o simulador também classifica os bloqueios conforme seus mecanismos internos, permitindo analisar se a requisição foi bloqueada por falta de recurso bruto, fragmentação local ou desalinhamento espectral.

## Políticas avaliadas

O simulador compara duas combinações de políticas:

- **FF/FF**: requisições small e large são alocadas com First-Fit;
- **FF/LF**: requisições small são alocadas com First-Fit e requisições large são alocadas com Last-Fit.

A política **First-Fit** seleciona o primeiro bloco contíguo disponível que atende à requisição. Já a política **Last-Fit** seleciona o último bloco contíguo disponível no espectro.

A comparação busca avaliar se o uso de Last-Fit para requisições de maior demanda espectral altera a organização do espectro e influencia a probabilidade de bloqueio da rede.

## Parâmetros principais

Os parâmetros utilizados estão alinhados aos experimentos finais apresentados na monografia:

- topologia com 12 nós;
- 28 enlaces direcionais;
- 132 pares origem-destino ordenados;
- 320 slots por enlace;
- 1.000.000 de requisições por simulação;
- cargas entre 50 e 50000 Erlang;
- tráfego dinâmico com chegadas e tempos de permanência exponenciais;
- classe small com 3 ou 5 slots, conforme a rota;
- classe large com 8 ou 10 slots, conforme a rota;
- roteamento por menor caminho fixo;
- seleção uniforme dos pares origem-destino;
- comparação pareada entre FF/FF e FF/LF para o mesmo fluxo de tráfego.

## Cenários de tráfego

O simulador executa automaticamente os três cenários de composição de tráfego avaliados na monografia:

| Cenário | Probabilidade de requisição small | Probabilidade de requisição large | Interpretação |
|---|---:|---:|---|
| 0,1 small | 0,1 | 0,9 | predominância de requisições large |
| 0,5 small | 0,5 | 0,5 | cenário balanceado entre classes |
| 0,9 small | 0,9 | 0,1 | predominância de requisições small |

Esses cenários permitem avaliar como a participação relativa das requisições large influencia a sensibilidade da rede à política de alocação espectral aplicada a essa classe.

## Métricas calculadas

O simulador calcula:

- probabilidade de bloqueio total;
- quantidade de requisições aceitas e bloqueadas;
- diferença de probabilidade de bloqueio entre FF/FF e FF/LF;
- ganho visual da política FF/LF em relação à política FF/FF;
- posição média das requisições large aceitas;
- distribuição das requisições large entre metade baixa e metade alta do espectro;
- classificação das causas de bloqueio em:
  - recurso bruto;
  - fragmentação local;
  - desalinhamento espectral.

O ganho visual é calculado como:

```text
G = Pb_FF/FF - Pb_FF/LF
```

Assim:

- `G > 0`: FF/LF reduziu a probabilidade de bloqueio em relação ao FF/FF;
- `G < 0`: FF/LF apresentou maior probabilidade de bloqueio em relação ao FF/FF;
- `G ≈ 0`: as duas políticas apresentaram desempenho semelhante.

## Saídas geradas

Ao final da execução, o simulador gera:

- arquivo de log com os resultados numéricos da simulação;
- gráficos da probabilidade de bloqueio em função da carga para cada cenário de tráfego;
- gráfico de ganho visual da política FF/LF em relação à FF/FF para os três cenários;
- gráfico de ganho visual em função da menor probabilidade de bloqueio observada entre as políticas.

Arquivos gerados:

```text
saida_simulacao.txt
pb_vs_erlang_0_1_small.png
pb_vs_erlang_0_5_small.png
pb_vs_erlang_0_9_small.png
ganho_visual_vs_erlang_tres_cenarios.png
ganho_visual_vs_pb_tres_cenarios.png
```

## Exemplo de resultado

A imagem abaixo apresenta o ganho visual da política FF/LF em relação à política FF/FF para os três cenários de composição de tráfego avaliados.

![Ganho visual da política FF/LF em relação à FF/FF](results/ganho_visual_vs_erlang_tres_cenarios.png)

## Estrutura do repositório

```text
avaliacao-politicas-eon/
│
├── results/
│   ├── pb_vs_erlang_0_1_small.png
│   ├── pb_vs_erlang_0_5_small.png
│   ├── pb_vs_erlang_0_9_small.png
│   ├── ganho_visual_vs_erlang_tres_cenarios.png
│   └── ganho_visual_vs_pb_tres_cenarios.png
│
├── src/
│   └── eon_spectrum_allocation_simulator.py
│
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## Como executar

Para executar o simulador, é necessário ter o Python instalado na máquina.

Primeiro, clone este repositório:

```bash
git clone https://github.com/EduardoLacerda-try/avaliacao-politicas-eon.git
```

Em seguida, acesse a pasta do projeto:

```bash
cd avaliacao-politicas-eon
```

Instale as dependências necessárias:

```bash
pip install -r requirements.txt
```

Execute o simulador:

```bash
python src/eon_spectrum_allocation_simulator.py
```

Ao final da execução, o simulador gera um arquivo de log com os resultados numéricos e os gráficos comparativos das políticas FF/FF e FF/LF nos três cenários de tráfego.

## Observação sobre tempo de execução

A versão final do simulador utiliza 1.000.000 de requisições por simulação e executa três cenários de tráfego, cada um com diferentes cargas em Erlang e comparação entre as políticas FF/FF e FF/LF.

Por esse motivo, a execução completa pode levar um tempo considerável, dependendo do desempenho da máquina utilizada.

Para realizar apenas um teste funcional rápido, é possível reduzir temporariamente o parâmetro:

```python
NUMERO_DE_REQUISICOES = 1_000_000
```

para um valor menor, como:

```python
NUMERO_DE_REQUISICOES = 10_000
```

Após o teste, recomenda-se retornar o valor para `1_000_000`, de modo a manter a configuração alinhada aos experimentos finais da monografia.

## Limitações do modelo

Este simulador foi desenvolvido com finalidade acadêmica, como parte de um Trabalho de Conclusão de Curso em Engenharia de Controle e Automação.

O modelo utiliza algumas simplificações, como:

- roteamento por menor caminho fixo;
- escolha uniforme dos pares origem-destino;
- ausência de conversão espectral;
- aproximação da demanda espectral pelo número de saltos da rota;
- não modelagem explícita de parâmetros físicos como OSNR, formato de modulação e penalidades da camada óptica.

Essas simplificações permitiram manter o escopo do estudo controlado e concentrar a análise na comparação entre as políticas FF/FF e FF/LF.

## Tecnologias utilizadas

- Python
- NumPy
- NetworkX
- Matplotlib
- Simulação de eventos discretos
- Modelagem computacional
- Análise de desempenho

## Trabalho relacionado

Este repositório está associado ao Trabalho de Conclusão de Curso:

**Avaliação de Políticas de Alocação Espectral em Redes Ópticas Elásticas com Tráfego Multiclasse**

Instituto Federal de Educação, Ciência e Tecnologia de São Paulo — Campus Guarulhos, 2026.

## Autor

**Eduardo da Silva Lacerda**  
Instituto Federal de Educação, Ciência e Tecnologia de São Paulo — Campus Guarulhos  
Bacharelado em Engenharia de Controle e Automação  

LinkedIn: [Eduardo da Silva Lacerda](https://www.linkedin.com/in/eduardo-da-silva-lacerda-b4b604296)

## Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo `LICENSE` para mais informações.
