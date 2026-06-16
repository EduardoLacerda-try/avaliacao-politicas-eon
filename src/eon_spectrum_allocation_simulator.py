import heapq
import time
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np



# -----------------------------------------------------------------------------
# Parametros principais
# -----------------------------------------------------------------------------

NUMERO_DE_REQUISICOES = 1_000_000
TAXA_OPERACAO = 1 / 1000
PROB_SMALL = 0.1
NUM_SLOTS = 320
N_REPLICACOES = 1

COMPARTILHAR_CAPACIDADE_ENTRE_DIRECOES = False
MEDIR_CAUSA_BLOQUEIO = True
WARMUP_REQUISICOES = 0

CENARIO_ESPECTRAL = "final_tcc"
ARQUIVO_LOG = "saida_simulacao.txt"
ARQUIVO_GRAFICO = "pb_vs_erlang.png"

CARGAS_ERLANG = [
    50, 100, 200, 400, 800, 1200, 1600, 2000, 3000, 4000,
    5000, 7000, 9000, 12000, 16000, 20000, 25000, 30000,
    35000, 40000, 45000, 50000,
]


# -----------------------------------------------------------------------------
# Topologia da rede
# -----------------------------------------------------------------------------

ADJACENCY_MATRIX = [
    [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
]


# -----------------------------------------------------------------------------
# Estruturas de dados
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Topologia:
    numero_de_nos: int
    numero_de_enlaces: int
    od_pairs: List[Tuple[int, int]]
    od_rotas: List[Tuple[int, ...]]
    od_hops: np.ndarray
    menores_caminhos: Dict[Tuple[int, int], List[int]]
    full_mask: int


@dataclass(frozen=True)
class StreamTrafego:
    interarrivals: np.ndarray
    holdings: np.ndarray
    is_small: np.ndarray
    od_indices: np.ndarray


@dataclass(frozen=True)
class CenarioEspectral:
    nome: str
    descricao_small: str
    descricao_large: str
    faixas_small_hops: Tuple[Tuple[int, int], ...]
    faixas_large_hops: Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class SlotsPorOD:
    small: np.ndarray
    large: np.ndarray
    cenario: CenarioEspectral


@dataclass
class ResultadoSimulacao:
    atendidas: int
    bloqueadas: int
    pb: float
    large_baixo: int
    large_alto: int
    posicao_media_large: float
    qtd_large_aceitas: int
    elapsed_s: float
    causa_bloqueio: Optional[Dict[str, int]] = None


# -----------------------------------------------------------------------------
# Log
# -----------------------------------------------------------------------------

log_file = None


def iniciar_log(nome_arquivo: str) -> None:
    global log_file
    log_file = open(nome_arquivo, "w", encoding="utf-8")


def fechar_log() -> None:
    global log_file
    if log_file is not None:
        log_file.close()
        log_file = None


def log(*args, **kwargs) -> None:
    texto = " ".join(str(a) for a in args)
    end = kwargs.get("end", "\n")

    print(texto, end=end)

    if log_file is not None:
        log_file.write(texto)
        if end != "":
            log_file.write(end)
        log_file.flush()


# -----------------------------------------------------------------------------
# Cenarios espectrais
# -----------------------------------------------------------------------------

def construir_cenario_espectral(nome: str) -> CenarioEspectral:
    cenarios = {
        "final_tcc": CenarioEspectral(
            nome="final_tcc",
            descricao_small="small = 3 ou 5 slots, conforme o numero de hops da rota",
            descricao_large="large = 8 ou 10 slots, conforme o numero de hops da rota",
            faixas_small_hops=((2, 3), (10_000, 5)),
            faixas_large_hops=((2, 8), (10_000, 10)),
        ),
        "fixo_basico": CenarioEspectral(
            nome="fixo_basico",
            descricao_small="small = 5 slots para qualquer rota",
            descricao_large="large = 12 slots para qualquer rota",
            faixas_small_hops=((10_000, 5),),
            faixas_large_hops=((10_000, 12),),
        ),
        "contraste_moderado": CenarioEspectral(
            nome="contraste_moderado",
            descricao_small="small = 3 ou 5 slots, conforme o numero de hops da rota",
            descricao_large="large = 7 ou 9 slots, conforme o numero de hops da rota",
            faixas_small_hops=((2, 3), (10_000, 5)),
            faixas_large_hops=((2, 7), (10_000, 9)),
        ),
    }

    if nome not in cenarios:
        disponiveis = ", ".join(sorted(cenarios))
        raise ValueError(f"Cenario espectral invalido: {nome}. Opcoes: {disponiveis}")

    return cenarios[nome]


def slots_por_hops(hops: int, faixas_hops: Tuple[Tuple[int, int], ...]) -> int:
    for max_hops, slots in faixas_hops:
        if hops <= max_hops:
            return slots
    raise RuntimeError(f"Nenhuma faixa definida para hops={hops}")


def precomputar_slots_por_od(topologia: Topologia, cenario: CenarioEspectral) -> SlotsPorOD:
    n_od = len(topologia.od_pairs)
    small = np.empty(n_od, dtype=np.uint8)
    large = np.empty(n_od, dtype=np.uint8)

    for od_idx in range(n_od):
        hops = int(topologia.od_hops[od_idx])
        small[od_idx] = slots_por_hops(hops, cenario.faixas_small_hops)
        large[od_idx] = slots_por_hops(hops, cenario.faixas_large_hops)

    return SlotsPorOD(small=small, large=large, cenario=cenario)


# -----------------------------------------------------------------------------
# Topologia e trafego
# -----------------------------------------------------------------------------

def construir_topologia(
    adjacency_matrix: List[List[int]],
    num_slots: int,
    compartilhar_direcoes: bool,
) -> Topologia:
    numero_de_nos = len(adjacency_matrix)
    grafo = nx.from_numpy_array(np.array(adjacency_matrix))

    menores_caminhos: Dict[Tuple[int, int], List[int]] = {}
    for origem in range(numero_de_nos):
        for destino in range(numero_de_nos):
            if origem != destino:
                menores_caminhos[(origem, destino)] = nx.dijkstra_path(grafo, origem, destino)

    mapa_enlaces: Dict[Tuple[int, int], int] = {}
    proximo_id = 0

    if compartilhar_direcoes:
        for i in range(numero_de_nos):
            for j in range(i + 1, numero_de_nos):
                if adjacency_matrix[i][j] or adjacency_matrix[j][i]:
                    mapa_enlaces[(i, j)] = proximo_id
                    mapa_enlaces[(j, i)] = proximo_id
                    proximo_id += 1
    else:
        for i in range(numero_de_nos):
            for j in range(numero_de_nos):
                if adjacency_matrix[i][j]:
                    mapa_enlaces[(i, j)] = proximo_id
                    proximo_id += 1

    od_pairs: List[Tuple[int, int]] = []
    od_rotas: List[Tuple[int, ...]] = []
    od_hops: List[int] = []

    for origem in range(numero_de_nos):
        for destino in range(numero_de_nos):
            if origem == destino:
                continue

            caminho_nos = menores_caminhos[(origem, destino)]
            caminho_enlaces = tuple(
                mapa_enlaces[(caminho_nos[i], caminho_nos[i + 1])]
                for i in range(len(caminho_nos) - 1)
            )

            od_pairs.append((origem, destino))
            od_rotas.append(caminho_enlaces)
            od_hops.append(len(caminho_enlaces))

    return Topologia(
        numero_de_nos=numero_de_nos,
        numero_de_enlaces=proximo_id,
        od_pairs=od_pairs,
        od_rotas=od_rotas,
        od_hops=np.array(od_hops, dtype=np.uint8),
        menores_caminhos=menores_caminhos,
        full_mask=(1 << num_slots) - 1,
    )


def gerar_stream_trafego(
    numero_de_requisicoes: int,
    carga_erlang: float,
    taxa_operacao: float,
    prob_small: float,
    numero_de_pares_od: int,
    seed: int,
) -> StreamTrafego:
    rng = np.random.default_rng(seed)
    taxa_chegadas = carga_erlang * taxa_operacao

    return StreamTrafego(
        interarrivals=rng.exponential(scale=1.0 / taxa_chegadas, size=numero_de_requisicoes),
        holdings=rng.exponential(scale=1.0 / taxa_operacao, size=numero_de_requisicoes),
        is_small=rng.random(numero_de_requisicoes) < prob_small,
        od_indices=rng.integers(0, numero_de_pares_od, size=numero_de_requisicoes, dtype=np.uint16),
    )


# -----------------------------------------------------------------------------
# Operacoes com bitsets
# -----------------------------------------------------------------------------

def candidatos_inicio(mask_livre: int, k: int) -> int:
    candidatos = mask_livre
    for shift in range(1, k):
        candidatos &= mask_livre >> shift
        if candidatos == 0:
            return 0
    return candidatos


def encontrar_inicio_ff(mask_livre: int, k: int) -> int:
    candidatos = candidatos_inicio(mask_livre, k)
    if candidatos == 0:
        return -1
    lsb = candidatos & -candidatos
    return lsb.bit_length() - 1


def encontrar_inicio_lf(mask_livre: int, k: int) -> int:
    candidatos = candidatos_inicio(mask_livre, k)
    if candidatos == 0:
        return -1
    return candidatos.bit_length() - 1


def classificar_causa_bloqueio(
    ocupacao_por_enlace: List[int],
    rota: Tuple[int, ...],
    k: int,
    full_mask: int,
) -> str:
    for enlace in rota:
        slots_livres = ((~ocupacao_por_enlace[enlace]) & full_mask).bit_count()
        if slots_livres < k:
            return "recurso_bruto"

    intersecao_candidatos = full_mask
    for enlace in rota:
        livres = (~ocupacao_por_enlace[enlace]) & full_mask
        candidatos = candidatos_inicio(livres, k)
        if candidatos == 0:
            return "fragmentacao_local"
        intersecao_candidatos &= candidatos

    if intersecao_candidatos == 0:
        return "desalinhamento"

    return "indefinido"


# -----------------------------------------------------------------------------
# Simulacao
# -----------------------------------------------------------------------------

def simular(
    topologia: Topologia,
    stream: StreamTrafego,
    num_slots: int,
    slots_por_od: SlotsPorOD,
    politica_large: str,
    warmup_requisicoes: int,
    medir_causa_bloqueio: bool,
) -> ResultadoSimulacao:
    if politica_large not in {"FF", "LF"}:
        raise ValueError(f"Politica invalida para large: {politica_large}")

    inicio_tempo = time.perf_counter()
    ocupacao_por_enlace = [0] * topologia.numero_de_enlaces
    fila_liberacoes: List[Tuple[float, int, int, int]] = []

    tempo_atual = 0.0
    event_id = 0
    atendidas = 0
    bloqueadas = 0
    large_baixo = 0
    large_alto = 0
    soma_posicao_large = 0.0
    qtd_large_aceitas = 0

    causa_bloqueio = None
    if medir_causa_bloqueio:
        causa_bloqueio = Counter()

    for i in range(len(stream.interarrivals)):
        tempo_atual += float(stream.interarrivals[i])

        while fila_liberacoes and fila_liberacoes[0][0] <= tempo_atual:
            _, _, od_idx_depart, bloco_mask_depart = heapq.heappop(fila_liberacoes)
            for enlace in topologia.od_rotas[od_idx_depart]:
                ocupacao_por_enlace[enlace] &= ~bloco_mask_depart

        od_idx = int(stream.od_indices[i])
        rota = topologia.od_rotas[od_idx]
        is_small = bool(stream.is_small[i])
        k = int(slots_por_od.small[od_idx]) if is_small else int(slots_por_od.large[od_idx])

        ocupacao_uniao = 0
        for enlace in rota:
            ocupacao_uniao |= ocupacao_por_enlace[enlace]

        mask_livre_comum = (~ocupacao_uniao) & topologia.full_mask
        inicio_bloco = encontrar_inicio_ff(mask_livre_comum, k)
        if not is_small and politica_large == "LF":
            inicio_bloco = encontrar_inicio_lf(mask_livre_comum, k)

        medindo = i >= warmup_requisicoes

        if inicio_bloco >= 0:
            bloco_mask = ((1 << k) - 1) << inicio_bloco

            for enlace in rota:
                ocupacao_por_enlace[enlace] |= bloco_mask

            event_id += 1
            tempo_saida = tempo_atual + float(stream.holdings[i])
            heapq.heappush(fila_liberacoes, (tempo_saida, event_id, od_idx, bloco_mask))

            if medindo:
                atendidas += 1
                if not is_small:
                    centro_bloco = inicio_bloco + (k - 1) / 2.0
                    soma_posicao_large += centro_bloco
                    qtd_large_aceitas += 1
                    if centro_bloco < num_slots / 2.0:
                        large_baixo += 1
                    else:
                        large_alto += 1
        else:
            if medindo:
                bloqueadas += 1
                if medir_causa_bloqueio and causa_bloqueio is not None:
                    causa = classificar_causa_bloqueio(
                        ocupacao_por_enlace=ocupacao_por_enlace,
                        rota=rota,
                        k=k,
                        full_mask=topologia.full_mask,
                    )
                    causa_bloqueio[causa] += 1

    total_medidas = atendidas + bloqueadas
    pb = bloqueadas / total_medidas if total_medidas > 0 else 0.0
    posicao_media = soma_posicao_large / qtd_large_aceitas if qtd_large_aceitas > 0 else float("nan")

    if causa_bloqueio is not None:
        causa_bloqueio = {
            "recurso_bruto": causa_bloqueio.get("recurso_bruto", 0),
            "fragmentacao_local": causa_bloqueio.get("fragmentacao_local", 0),
            "desalinhamento": causa_bloqueio.get("desalinhamento", 0),
            "indefinido": causa_bloqueio.get("indefinido", 0),
        }

    return ResultadoSimulacao(
        atendidas=atendidas,
        bloqueadas=bloqueadas,
        pb=pb,
        large_baixo=large_baixo,
        large_alto=large_alto,
        posicao_media_large=posicao_media,
        qtd_large_aceitas=qtd_large_aceitas,
        elapsed_s=time.perf_counter() - inicio_tempo,
        causa_bloqueio=causa_bloqueio,
    )


# -----------------------------------------------------------------------------
# Relatorios e grafico
# -----------------------------------------------------------------------------

def formatar_distribuicao_slots(arr: np.ndarray) -> str:
    contagem = Counter(arr.tolist())
    return ", ".join(f"{slots}:{contagem[slots]} OD" for slots in sorted(contagem))


def imprimir_resumo(carga: float, politica_large: str, resultado: ResultadoSimulacao) -> None:
    log("-" * 70)
    log(f"Carga: {carga} Erlang | politica large: {politica_large}")
    log("-" * 70)
    log(f"Pb: {resultado.pb:.6f}")
    log(f"Atendidas: {resultado.atendidas}")
    log(f"Bloqueadas: {resultado.bloqueadas}")
    log(f"Tempo de execucao: {resultado.elapsed_s:.2f}s")

    if resultado.qtd_large_aceitas > 0:
        log(f"Large na metade baixa: {resultado.large_baixo}")
        log(f"Large na metade alta: {resultado.large_alto}")
        log(f"Posicao media large: {resultado.posicao_media_large:.2f}")

    if resultado.causa_bloqueio is not None:
        log("Causas de bloqueio:")
        log(f"  recurso bruto: {resultado.causa_bloqueio['recurso_bruto']}")
        log(f"  fragmentacao local: {resultado.causa_bloqueio['fragmentacao_local']}")
        log(f"  desalinhamento: {resultado.causa_bloqueio['desalinhamento']}")
        log(f"  indefinido: {resultado.causa_bloqueio['indefinido']}")
    log()


def gerar_grafico_pb(cargas: List[float], pb_ff_ff: List[float], pb_ff_lf: List[float]) -> None:
    plt.figure(figsize=(10, 6))
    plt.plot(cargas, pb_ff_ff, marker="o", label="FF/FF")
    plt.plot(cargas, pb_ff_lf, marker="s", label="FF/LF")
    plt.xlabel("Carga (Erlang)", fontsize=12)
    plt.ylabel("Probabilidade de bloqueio (Pb)", fontsize=12)
    plt.title("Probabilidade de bloqueio em funcao da carga")
    plt.grid(True)
    plt.legend()
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.savefig(ARQUIVO_GRAFICO, dpi=300)
    plt.show()


# -----------------------------------------------------------------------------
# Execucao principal
# -----------------------------------------------------------------------------

def main() -> None:
    iniciar_log(ARQUIVO_LOG)

    try:
        cenario = construir_cenario_espectral(CENARIO_ESPECTRAL)
        topologia = construir_topologia(
            adjacency_matrix=ADJACENCY_MATRIX,
            num_slots=NUM_SLOTS,
            compartilhar_direcoes=COMPARTILHAR_CAPACIDADE_ENTRE_DIRECOES,
        )
        slots_por_od = precomputar_slots_por_od(topologia, cenario)

        log("=" * 70)
        log("Simulador de EON - comparacao FF/FF x FF/LF")
        log("=" * 70)
        log(f"Nos: {topologia.numero_de_nos}")
        log(f"Enlaces modelados: {topologia.numero_de_enlaces}")
        log(f"Pares OD: {len(topologia.od_pairs)}")
        log(f"Slots por enlace: {NUM_SLOTS}")
        log(f"Requisicoes por simulacao: {NUMERO_DE_REQUISICOES}")
        log(f"Probabilidade de requisicao small: {PROB_SMALL}")
        log(f"Cenario espectral: {cenario.nome}")
        log(f"{cenario.descricao_small}")
        log(f"{cenario.descricao_large}")
        log(f"Distribuicao small por OD: {formatar_distribuicao_slots(slots_por_od.small)}")
        log(f"Distribuicao large por OD: {formatar_distribuicao_slots(slots_por_od.large)}")
        log("=" * 70)
        log()

        resultados_ff_ff: List[float] = []
        resultados_ff_lf: List[float] = []

        for carga in CARGAS_ERLANG:
            pbs_ff_ff = []
            pbs_ff_lf = []

            log(f"===== Carga {carga} Erlang =====")

            for rep in range(N_REPLICACOES):
                seed = int(1000 + carga * 100 + rep)
                stream = gerar_stream_trafego(
                    numero_de_requisicoes=NUMERO_DE_REQUISICOES,
                    carga_erlang=carga,
                    taxa_operacao=TAXA_OPERACAO,
                    prob_small=PROB_SMALL,
                    numero_de_pares_od=len(topologia.od_pairs),
                    seed=seed,
                )

                resultado_ff_ff = simular(
                    topologia=topologia,
                    stream=stream,
                    num_slots=NUM_SLOTS,
                    slots_por_od=slots_por_od,
                    politica_large="FF",
                    warmup_requisicoes=WARMUP_REQUISICOES,
                    medir_causa_bloqueio=MEDIR_CAUSA_BLOQUEIO,
                )

                resultado_ff_lf = simular(
                    topologia=topologia,
                    stream=stream,
                    num_slots=NUM_SLOTS,
                    slots_por_od=slots_por_od,
                    politica_large="LF",
                    warmup_requisicoes=WARMUP_REQUISICOES,
                    medir_causa_bloqueio=MEDIR_CAUSA_BLOQUEIO,
                )

                imprimir_resumo(carga, "FF", resultado_ff_ff)
                imprimir_resumo(carga, "LF", resultado_ff_lf)

                pbs_ff_ff.append(resultado_ff_ff.pb)
                pbs_ff_lf.append(resultado_ff_lf.pb)

            media_ff_ff = float(np.mean(pbs_ff_ff))
            media_ff_lf = float(np.mean(pbs_ff_lf))
            delta = media_ff_lf - media_ff_ff

            resultados_ff_ff.append(media_ff_ff)
            resultados_ff_lf.append(media_ff_lf)

            log("Resumo da carga")
            log(f"Pb medio FF/FF: {media_ff_ff:.6f}")
            log(f"Pb medio FF/LF: {media_ff_lf:.6f}")
            log(f"Delta Pb (FF/LF - FF/FF): {delta:+.6f}")
            log()

        gerar_grafico_pb(CARGAS_ERLANG, resultados_ff_ff, resultados_ff_lf)

    finally:
        fechar_log()


if __name__ == "__main__":
    main()
