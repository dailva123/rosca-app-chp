# tabelas.py
#
# Tabelas de referência para identificação de roscas a partir do diâmetro
# medido na foto (rosca externa = diâmetro maior/crista; rosca interna =
# diâmetro do furo, aproximado pelo diâmetro menor/raiz da rosca que nela
# se encaixa).
#
# As colunas (diâmetro nominal em mm e fios por polegada - TPI) seguem as
# normas oficiais de cada padrão:
#   BSPP (ISO 228 / DIN 259, rosca "G")  - paralela, usada em conexões
#       hidráulicas e pneumáticas (vedação por anel/o-ring ou junta).
#   BSPT (ISO 7-1 / DIN 2999, rosca "R"/"Rc") - cônica, vedação pelo
#       próprio rosqueamento (fita veda-rosca / pasta).
#   NPT  (ASME B1.20.1) - cônica, padrão americano equivalente ao BSPT.
#   UNC  (ASME B1.1) - rosca americana grossa (parafusos/porcas).
#   UNF  (ASME B1.1) - rosca americana fina (parafusos/porcas).
#
# BSPP e BSPT compartilham o mesmo diâmetro nominal e passo (mesma série
# de rosca de tubo), diferindo apenas pela forma: BSPP é cilíndrica (reta)
# e BSPT é cônica (afunila). Por isso, quando o diâmetro medido bater com
# essa série, os dois candidatos aparecem juntos e é preciso olhar a peça
# para saber se ela afunila (BSPT/NPT) ou é reta (BSPP).

ANGULO_FILETE = {
    "BSPP": 55,
    "BSPT": 55,
    "NPT": 60,
    "UNC": 60,
    "UNF": 60,
}

FORMA_ROSCA = {
    "BSPP": "cilíndrica (paralela)",
    "BSPT": "cônica (afunilada)",
    "NPT": "cônica (afunilada)",
    "UNC": "cilíndrica (paralela)",
    "UNF": "cilíndrica (paralela)",
}

DESCRICAO_NORMA = {
    "BSPP": "Rosca paralela de tubo (British Standard Pipe Parallel) - vedação por anel/junta",
    "BSPT": "Rosca cônica de tubo (British Standard Pipe Taper) - vedação pelo rosqueamento",
    "NPT": "Rosca cônica americana (National Pipe Taper) - vedação pelo rosqueamento",
    "UNC": "Rosca americana grossa (Unified National Coarse)",
    "UNF": "Rosca americana fina (Unified National Fine)",
}

# (diametro_nominal_mm, tpi) por bitola
_DIAMETRO_TPI_TUBO = {
    "1/16": (7.723, 28), "1/8": (9.728, 28), "1/4": (13.157, 19), "3/8": (16.662, 19),
    "1/2": (20.955, 14), "5/8": (22.911, 14), "3/4": (26.441, 14), "7/8": (30.201, 14),
    "1": (33.249, 11), "1.1/8": (37.897, 11), "1.1/4": (41.910, 11), "1.3/8": (44.323, 11),
    "1.1/2": (47.803, 11), "1.3/4": (53.746, 11), "2": (59.614, 11), "2.1/4": (65.710, 11),
    "2.1/2": (75.184, 11), "2.3/4": (81.534, 11), "3": (87.884, 11), "3.1/2": (100.330, 11),
    "4": (113.030, 11),
}

DIAMETRO_TPI = {
    "BSPP": dict(_DIAMETRO_TPI_TUBO),
    "BSPT": dict(_DIAMETRO_TPI_TUBO),
    "NPT": {
        "1/16": (7.938, 27), "1/8": (10.287, 27), "1/4": (13.716, 18), "3/8": (17.145, 18),
        "1/2": (21.336, 14), "3/4": (26.670, 14), "1": (33.401, 11.5), "1.1/4": (42.164, 11.5),
        "1.1/2": (48.260, 11.5), "2": (60.325, 11.5), "2.1/2": (73.025, 8), "3": (88.900, 8),
        "3.1/2": (101.600, 8), "4": (114.300, 8),
    },
    "UNC": {
        "#4": (2.845, 40), "#6": (3.505, 32), "#8": (4.166, 32), "#10": (4.826, 24),
        "1/4": (6.350, 20), "5/16": (7.938, 18), "3/8": (9.525, 16), "7/16": (11.113, 14),
        "1/2": (12.700, 13), "9/16": (14.288, 12), "5/8": (15.875, 11), "3/4": (19.050, 10),
        "7/8": (22.225, 9), "1": (25.400, 8), "1.1/8": (28.575, 7), "1.1/4": (31.750, 7),
        "1.3/8": (34.925, 6), "1.1/2": (38.100, 6),
    },
    "UNF": {
        "#4": (2.845, 48), "#6": (3.505, 40), "#8": (4.166, 36), "#10": (4.826, 32),
        "1/4": (6.350, 28), "5/16": (7.938, 24), "3/8": (9.525, 24), "7/16": (11.113, 20),
        "1/2": (12.700, 20), "9/16": (14.288, 18), "5/8": (15.875, 18), "3/4": (19.050, 16),
        "7/8": (22.225, 14), "1": (25.400, 12), "1.1/8": (28.575, 12), "1.1/4": (31.750, 12),
        "1.3/8": (34.925, 12), "1.1/2": (38.100, 12),
    },
}


def _profundidade_filete_mm(passo_mm: float, angulo: int) -> float:
    """Profundidade aproximada do filete (altura total), usada para estimar
    o diâmetro do furo de uma rosca interna a partir do diâmetro nominal
    (externo) da mesma bitola. Whitworth (55°) e Unified/NPT (60°) têm
    proporções ligeiramente diferentes."""
    fator = 1.2806 if angulo == 55 else 1.2269
    return fator * passo_mm


def _construir_tabela():
    tabela = {}
    for norma, bitolas in DIAMETRO_TPI.items():
        angulo = ANGULO_FILETE[norma]
        externa, interna = {}, {}
        for bitola, (diametro_nominal, tpi) in bitolas.items():
            passo_mm = 25.4 / tpi
            profundidade = _profundidade_filete_mm(passo_mm, angulo)
            externa[bitola] = {
                "diametro_mm": round(diametro_nominal, 3),
                "passo_mm": round(passo_mm, 4),
                "tpi": tpi,
            }
            interna[bitola] = {
                "diametro_mm": round(diametro_nominal - profundidade, 3),
                "passo_mm": round(passo_mm, 4),
                "tpi": tpi,
            }
        tabela[norma] = {"externa": externa, "interna": interna}
    return tabela


# Estrutura final: TABELAS[norma][tipo][bitola] = {"diametro_mm", "passo_mm", "tpi"}
TABELAS = _construir_tabela()

# Mantido por compatibilidade com código legado que importava TABELA_ROSCAS.
TABELA_ROSCAS = TABELAS


def mm_para_polegada(mm: float) -> float:
    return round(mm / 25.4, 3)


def encontrar_candidatos(diametro_medido_mm: float, interna: bool, top_n: int = 3):
    """Retorna os `top_n` padrões de rosca mais prováveis para o diâmetro
    medido, ordenados do mais para o menos provável, cada um com uma
    estimativa de confiança."""
    tipo = "interna" if interna else "externa"
    candidatos = []

    for norma, dados in TABELAS.items():
        for bitola, info in dados[tipo].items():
            diferenca = abs(diametro_medido_mm - info["diametro_mm"])
            candidatos.append({
                "norma": norma,
                "descricao": DESCRICAO_NORMA[norma],
                "forma": FORMA_ROSCA[norma],
                "bitola_pol": bitola,
                "diametro_ref_mm": info["diametro_mm"],
                "passo_mm": info["passo_mm"],
                "tpi": info["tpi"],
                "diferenca_mm": round(diferenca, 3),
                "confianca": _confianca_por_diferenca(diferenca),
            })

    candidatos.sort(key=lambda c: c["diferenca_mm"])
    return candidatos[:top_n]


def _confianca_por_diferenca(diferenca_mm: float) -> float:
    if diferenca_mm <= 0.2:
        return 99.0
    if diferenca_mm <= 0.5:
        return 90.0
    if diferenca_mm <= 1.0:
        return 75.0
    if diferenca_mm <= 2.0:
        return 55.0
    return max(10.0, round(30.0 - diferenca_mm, 1))
