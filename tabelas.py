# tabelas.py
#
# Tabelas de referência para identificação de roscas de tubo/conexão
# hidráulica e pneumática, a partir do diâmetro medido na foto (rosca
# externa = diâmetro maior/crista; rosca interna = diâmetro do furo,
# aproximado pelo diâmetro menor/raiz da rosca que nela se encaixa).
#
# Cobre só normas de rosca de TUBO (conexões hidráulicas/pneumáticas),
# não rosca de parafuso/porca (UNC/UNF ficam de fora de propósito):
#   BSPP (ISO 228 / DIN 259, rosca "G")  - paralela (cilíndrica), usada em
#       conexões hidráulicas e pneumáticas (vedação por anel/o-ring ou junta).
#   BSPT (ISO 7-1 / DIN 2999, rosca "R"/"Rc") - cônica, vedação pelo
#       próprio rosqueamento (fita veda-rosca / pasta).
#   NPT  (ASME B1.20.1) - cônica, padrão americano equivalente ao BSPT.
#
# BSPP e BSPT compartilham o mesmo diâmetro nominal e passo (mesma série
# de rosca de tubo), diferindo apenas pela forma: BSPP é cilíndrica (reta)
# e BSPT é cônica (afunila). BSPT e NPT, por sua vez, são as duas cônicas e
# têm diâmetros muito próximos entre si. Por isso o diâmetro sozinho não
# resolve tudo: encontrar_candidatos aceita um parâmetro opcional `formato`
# ("reta" ou "conica", vindo de uma pergunta simples ao usuário) para
# eliminar de cara os candidatos com o formato errado.

ANGULO_FILETE = {
    "BSPP": 55,
    "BSPT": 55,
    "NPT": 60,
}

FORMA_ROSCA = {
    "BSPP": "cilíndrica (paralela)",
    "BSPT": "cônica (afunilada)",
    "NPT": "cônica (afunilada)",
}

DESCRICAO_NORMA = {
    "BSPP": "Rosca paralela de tubo (British Standard Pipe Parallel) - vedação por anel/junta",
    "BSPT": "Rosca cônica de tubo (British Standard Pipe Taper) - vedação pelo rosqueamento",
    "NPT": "Rosca cônica americana (National Pipe Taper) - vedação pelo rosqueamento",
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


def encontrar_candidatos(diametro_medido_mm: float, interna: bool, formato: str = None, top_n: int = 3):
    """Retorna os `top_n` padrões de rosca mais prováveis para o diâmetro
    medido, ordenados do mais para o menos provável, cada um com uma
    estimativa de confiança.

    `formato` é opcional: "reta" (cilíndrica/paralela) ou "conica"
    (afunilada). Quando informado, já elimina de cara as normas com o
    formato errado, resolvendo a ambiguidade que o diâmetro sozinho não
    resolve (ex.: BSPP x BSPT têm o mesmo diâmetro nominal)."""
    tipo = "interna" if interna else "externa"
    normas = TABELAS.items()
    if formato == "reta":
        normas = [(n, d) for n, d in normas if "paralela" in FORMA_ROSCA[n]]
    elif formato == "conica":
        normas = [(n, d) for n, d in normas if "afunilada" in FORMA_ROSCA[n]]

    candidatos = []

    for norma, dados in normas:
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
