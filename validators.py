"""Validações de dados. Cada função retorna None se OK, ou a mensagem de erro."""
import re
from datetime import date, datetime

TIPOS_PRODUTO = ("medicamento", "higiene", "cosmetico")
PERFIS = ("admin", "farmaceutico", "atendente")


def nome(valor):
    if not valor or len(valor.strip().split()) < 2:
        return "Informe o nome completo (nome e sobrenome)"
    return None


def email(valor):
    if not valor or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", valor):
        return "E-mail inválido"
    return None


def telefone(valor):
    digitos = re.sub(r"\D", "", valor or "")
    if len(digitos) not in (10, 11):
        return "Telefone inválido (use DDD + número)"
    return None


def senha(valor):
    if not valor or len(valor) < 6:
        return "A senha deve ter pelo menos 6 caracteres"
    return None


def cnpj(valor):
    d = re.sub(r"\D", "", valor or "")
    if len(d) != 14 or d == d[0] * 14:
        return "CNPJ inválido"

    def digito(base):
        pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if len(base) == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        resto = sum(int(n) * p for n, p in zip(base, pesos)) % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = digito(d[:12])
    d2 = digito(d[:12] + d1)
    return None if d[12:] == d1 + d2 else "CNPJ inválido"


def inteiro_positivo(valor, campo):
    if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
        return f"{campo} deve ser um número inteiro maior que zero"
    return None


def inteiro_nao_negativo(valor, campo):
    if not isinstance(valor, int) or isinstance(valor, bool) or valor < 0:
        return f"{campo} deve ser um número inteiro maior ou igual a zero"
    return None


def preco(valor, campo):
    if not isinstance(valor, (int, float)) or isinstance(valor, bool) or valor <= 0:
        return f"{campo} deve ser maior que zero"
    return None


def data(valor):
    try:
        datetime.strptime(valor, "%Y-%m-%d")
        return None
    except (TypeError, ValueError):
        return "Data inválida (use AAAA-MM-DD)"


def validade_nao_vencida(valor, hoje=None):
    """Para compras: a data deve ser válida e não pode estar vencida."""
    msg = data(valor)
    if msg:
        return "Validade inválida (use AAAA-MM-DD)"
    if date.fromisoformat(valor) < (hoje or date.today()):
        return "Não é possível comprar lote com validade vencida"
    return None
