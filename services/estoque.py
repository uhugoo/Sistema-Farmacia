"""Regras de estoque por lote: status da validade e escolha de lotes pelo FEFO."""
from datetime import date, timedelta

DIAS_ALERTA = 30


class EstoqueInsuficiente(Exception):
    def __init__(self, disponivel):
        super().__init__(f"Estoque insuficiente (disponível: {disponivel})")
        self.disponivel = disponivel


def _como_data(valor):
    return date.fromisoformat(valor) if isinstance(valor, str) else valor


def status_lote(validade, hoje=None, dias=DIAS_ALERTA):
    """'vencido', 'vence_em_breve' (até `dias` dias) ou 'ok'."""
    hoje = hoje or date.today()
    v = _como_data(validade)
    if v < hoje:
        return "vencido"
    if v <= hoje + timedelta(days=dias):
        return "vence_em_breve"
    return "ok"


def escolher_lotes(lotes, quantidade, hoje=None):
    """FEFO (first expired, first out): consome primeiro o lote que vence antes.

    `lotes` é uma lista de dicts com id, validade e quantidade.
    Lotes vencidos ou zerados são ignorados.
    Retorna [(lote_id, quantidade_usada)] ou levanta EstoqueInsuficiente.
    """
    hoje = hoje or date.today()
    validos = sorted(
        (l for l in lotes if l["quantidade"] > 0 and status_lote(l["validade"], hoje) != "vencido"),
        key=lambda l: (str(l["validade"]), l["id"]),
    )
    disponivel = sum(l["quantidade"] for l in validos)
    if quantidade > disponivel:
        raise EstoqueInsuficiente(disponivel)
    escolhidos, falta = [], quantidade
    for lote in validos:
        if falta == 0:
            break
        usar = min(lote["quantidade"], falta)
        escolhidos.append((lote["id"], usar))
        falta -= usar
    return escolhidos
