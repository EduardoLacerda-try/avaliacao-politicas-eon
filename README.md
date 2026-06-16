# Avaliação de Políticas de Alocação Espectral em Redes Ópticas Elásticas

Este repositório contém o simulador desenvolvido para o Trabalho de Conclusão de Curso intitulado **"Avaliação de Políticas de Alocação Espectral em Redes Ópticas Elásticas com Tráfego Multiclasse"**.

O objetivo do simulador é comparar políticas de alocação espectral em Redes Ópticas Elásticas (Elastic Optical Networks - EONs), considerando tráfego dinâmico multiclasse e restrições de contiguidade, continuidade e não sobreposição de slots.

## Políticas avaliadas

O simulador compara duas combinações de políticas:

- **FF/FF**: requisições small e large alocadas com First-Fit;
- **FF/LF**: requisições small alocadas com First-Fit e requisições large alocadas com Last-Fit.

## Parâmetros principais

Os parâmetros utilizados estão alinhados aos experimentos finais apresentados na monografia:

- Topologia com 12 nós;
- 28 enlaces direcionais;
- 132 pares origem-destino ordenados;
- 320 slots por enlace;
- 1.000.000 de requisições por simulação;
- Cargas entre 50 e 50000 Erlang;
- Tráfego dinâmico com chegadas e tempos de permanência exponenciais;
- Classe small com 3 ou 5 slots, conforme a rota;
- Classe large com 8 ou 10 slots, conforme a rota.

## Métricas calculadas

O simulador calcula:

- probabilidade de bloqueio total;
- quantidade de requisições aceitas e bloqueadas;
- posição média das requisições large aceitas;
- distribuição das requisições large entre metade baixa e metade alta do espectro;
- classificação das causas de bloqueio:
  - recurso bruto;
  - fragmentação local;
  - desalinhamento espectral.

## Como executar

Clone o repositório:

```bash
git clone https://github.com/SEU-USUARIO/avaliacao-politicas-eon.git
cd avaliacao-politicas-eon
