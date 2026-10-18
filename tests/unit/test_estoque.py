import unittest
from datetime import date
from services.estoque import EstoqueInsuficiente, escolher_lotes, status_lote

HOJE = date(2026, 6, 15)


class TestStatusLote(unittest.TestCase):
    def test_status(self):
        self.assertEqual(status_lote("2026-06-14", HOJE), "vencido")
        self.assertEqual(status_lote("2026-06-15", HOJE), "vence_em_breve")
        self.assertEqual(status_lote("2026-07-15", HOJE), "vence_em_breve")
        self.assertEqual(status_lote("2026-07-16", HOJE), "ok")


class TestFEFO(unittest.TestCase):
    def lotes(self):
        return [
            {"id": 1, "validade": "2027-06-01", "quantidade": 10},
            {"id": 2, "validade": "2026-09-01", "quantidade": 5},
            {"id": 3, "validade": "2026-01-01", "quantidade": 50},  # vencido
            {"id": 4, "validade": "2026-12-01", "quantidade": 0},   # zerado
        ]

    def test_usa_primeiro_o_lote_que_vence_antes(self):
        self.assertEqual(escolher_lotes(self.lotes(), 3, HOJE), [(2, 3)])

    def test_divide_entre_lotes(self):
        self.assertEqual(escolher_lotes(self.lotes(), 8, HOJE), [(2, 5), (1, 3)])

    def test_ignora_vencidos_e_zerados(self):
        self.assertEqual(escolher_lotes(self.lotes(), 15, HOJE), [(2, 5), (1, 10)])

    def test_estoque_insuficiente_informa_disponivel(self):
        with self.assertRaises(EstoqueInsuficiente) as ctx:
            escolher_lotes(self.lotes(), 16, HOJE)
        self.assertEqual(ctx.exception.disponivel, 15)

    def test_sem_lotes(self):
        with self.assertRaises(EstoqueInsuficiente):
            escolher_lotes([], 1, HOJE)
