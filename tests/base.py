import os
import tempfile
import unittest
from datetime import date, timedelta
from app import create_app


def dias(n):
    """Data (AAAA-MM-DD) daqui a n dias; n negativo = no passado."""
    return (date.today() + timedelta(days=n)).isoformat()


class BaseTest(unittest.TestCase):
    """Cria um banco temporário novo para cada teste."""

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp(suffix=".db")
        self.app = create_app({"DATABASE": self.path, "TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.path)

    # --- helpers ---
    def hdr(self, email, senha):
        r = self.client.post("/api/auth/login", json={"email": email, "senha": senha})
        return {"Authorization": "Bearer " + r.get_json()["token"]}

    def admin(self):
        return self.hdr("admin@farmacia.com", "admin123")

    def novo_usuario(self, perfil, n=1):
        d = {"nome_completo": f"Pessoa Teste{n}", "email": f"{perfil}{n}@teste.com",
             "telefone": "75988887777", "senha": "senha123", "perfil": perfil}
        r = self.client.post("/api/usuarios", json=d, headers=self.admin())
        self.assertEqual(r.status_code, 201, r.get_json())
        return r.get_json()["id"], self.hdr(d["email"], d["senha"])

    def novo_produto(self, hdr, nome="Dipirona 500mg", tipo="medicamento", preco=10.0, minimo=0, receita=False):
        r = self.client.post("/api/produtos", headers=hdr, json={
            "nome": nome, "tipo": tipo, "preco_venda": preco, "estoque_minimo": minimo, "exige_receita": receita})
        self.assertEqual(r.status_code, 201, r.get_json())
        return r.get_json()["id"]

    def novo_fornecedor(self, hdr, nome="Distribuidora Saude", cnpj="11.222.333/0001-81"):
        r = self.client.post("/api/fornecedores", headers=hdr,
                             json={"nome": nome, "cnpj": cnpj, "telefone": "7533334444"})
        self.assertEqual(r.status_code, 201, r.get_json())
        return r.get_json()["id"]

    def comprar(self, hdr, fornecedor_id, produto_id, lote="L1", validade=None, qtd=10, custo=5.0):
        return self.client.post("/api/compras", headers=hdr, json={
            "fornecedor_id": fornecedor_id,
            "itens": [{"produto_id": produto_id, "codigo_lote": lote, "validade": validade or dias(365),
                       "quantidade": qtd, "custo_unitario": custo}]})

    def vender(self, hdr, produto_id, qtd, **extra):
        return self.client.post("/api/vendas", headers=hdr,
                                json={"itens": [{"produto_id": produto_id, "quantidade": qtd}], **extra})

    def estoque_total(self, hdr, produto_id):
        prods = self.client.get("/api/produtos", headers=hdr).get_json()
        return [p for p in prods if p["id"] == produto_id][0]["estoque_total"]
