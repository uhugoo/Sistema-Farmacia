from tests.base import BaseTest, dias


class TestAcesso(BaseTest):
    def test_login_valido_e_invalido(self):
        r = self.client.post("/api/auth/login", json={"email": "admin@farmacia.com", "senha": "admin123"})
        self.assertEqual(r.get_json()["perfil"], "admin")
        r = self.client.post("/api/auth/login", json={"email": "admin@farmacia.com", "senha": "errada"})
        self.assertEqual(r.status_code, 401)

    def test_sem_token(self):
        self.assertEqual(self.client.get("/api/produtos").status_code, 401)

    def test_permissoes_por_perfil(self):
        _, atend = self.novo_usuario("atendente")
        _, farm = self.novo_usuario("farmaceutico")
        self.assertEqual(self.client.get("/api/usuarios", headers=farm).status_code, 403)
        self.assertEqual(self.client.post("/api/produtos", headers=atend,
                         json={"nome": "Abc", "tipo": "higiene", "preco_venda": 5}).status_code, 403)
        self.assertEqual(self.client.get("/api/dashboard", headers=atend).status_code, 403)
        self.assertEqual(self.client.get("/api/compras", headers=atend).status_code, 403)
        self.assertEqual(self.client.get("/api/estoque", headers=atend).status_code, 200)
        self.assertEqual(self.client.get("/api/dashboard", headers=farm).status_code, 200)


class TestUsuarios(BaseTest):
    def test_cadastro_e_remocao(self):
        adm = self.admin()
        uid, _ = self.novo_usuario("atendente")
        emails = [u["email"] for u in self.client.get("/api/usuarios", headers=adm).get_json()]
        self.assertIn("atendente1@teste.com", emails)
        self.assertEqual(self.client.delete(f"/api/usuarios/{uid}", headers=adm).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/usuarios/{uid}", headers=adm).status_code, 404)

    def test_validacoes(self):
        adm = self.admin()
        self.novo_usuario("atendente")
        base = {"nome_completo": "Pessoa Teste", "email": "x@y.com", "telefone": "75988887777", "senha": "abc123", "perfil": "atendente"}
        self.assertEqual(self.client.post("/api/usuarios", headers=adm, json={**base, "email": "atendente1@teste.com"}).status_code, 409)
        for campo, valor in (("email", "invalido"), ("telefone", "123"), ("senha", "1"), ("nome_completo", "Um"), ("perfil", "chefe")):
            r = self.client.post("/api/usuarios", headers=adm, json={**base, campo: valor})
            self.assertEqual(r.status_code, 400, campo)

    def test_admin_nao_remove_a_si_mesmo(self):
        self.assertEqual(self.client.delete("/api/usuarios/1", headers=self.admin()).status_code, 400)

    def test_usuario_com_vendas_nao_pode_ser_removido(self):
        adm = self.admin()
        pid = self.novo_produto(adm)
        self.comprar(adm, self.novo_fornecedor(adm), pid)
        uid, atend = self.novo_usuario("atendente")
        self.assertEqual(self.vender(atend, pid, 1).status_code, 201)
        self.assertEqual(self.client.delete(f"/api/usuarios/{uid}", headers=adm).status_code, 409)


class TestProdutos(BaseTest):
    def test_crud_e_filtros(self):
        adm = self.admin()
        pid = self.novo_produto(adm, "Dipirona 500mg")
        self.novo_produto(adm, "Sabonete Neutro", "higiene")
        self.novo_produto(adm, "Hidratante Facial", "cosmetico")
        r = self.client.get("/api/produtos?tipo=higiene", headers=adm).get_json()
        self.assertEqual([p["nome"] for p in r], ["Sabonete Neutro"])
        self.assertEqual(len(self.client.get("/api/produtos?q=dipi", headers=adm).get_json()), 1)
        r = self.client.put(f"/api/produtos/{pid}", headers=adm,
                            json={"nome": "Dipirona 1g", "tipo": "medicamento", "preco_venda": 12.5})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.delete(f"/api/produtos/{pid}", headers=adm).status_code, 200)

    def test_validacoes(self):
        adm = self.admin()
        self.novo_produto(adm)
        base = {"nome": "Novo Produto", "tipo": "higiene", "preco_venda": 5}
        for campo, valor in (("tipo", "brinquedo"), ("preco_venda", 0), ("preco_venda", -3), ("estoque_minimo", -1), ("nome", "")):
            r = self.client.post("/api/produtos", headers=adm, json={**base, campo: valor})
            self.assertEqual(r.status_code, 400, campo)
        self.assertEqual(self.client.post("/api/produtos", headers=adm, json={**base, "nome": "Dipirona 500mg"}).status_code, 409)

    def test_produto_com_movimentacao_nao_pode_ser_removido(self):
        adm = self.admin()
        pid = self.novo_produto(adm)
        self.comprar(adm, self.novo_fornecedor(adm), pid)
        self.assertEqual(self.client.delete(f"/api/produtos/{pid}", headers=adm).status_code, 409)


class TestFornecedores(BaseTest):
    def test_cnpj_invalido_e_duplicado(self):
        adm = self.admin()
        self.novo_fornecedor(adm)
        r = self.client.post("/api/fornecedores", headers=adm, json={"nome": "Outro", "cnpj": "11.222.333/0001-82", "telefone": "7533334444"})
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/fornecedores", headers=adm, json={"nome": "Outro", "cnpj": "11222333000181", "telefone": "7533334444"})
        self.assertEqual(r.status_code, 409)


class TestCompras(BaseTest):
    def test_compra_cria_lote_e_atualiza_estoque(self):
        adm = self.admin()
        pid, fid = self.novo_produto(adm), self.novo_fornecedor(adm)
        r = self.comprar(adm, fid, pid, "L1", qtd=10, custo=4.5)
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertEqual(r.get_json()["valor_total"], 45.0)
        self.assertEqual(self.estoque_total(adm, pid), 10)
        self.comprar(adm, fid, pid, "L1", qtd=5)          # mesmo lote: soma
        self.assertEqual(self.estoque_total(adm, pid), 15)
        self.assertEqual(len(self.client.get("/api/estoque", headers=adm).get_json()), 1)
        self.comprar(adm, fid, pid, "L2", qtd=3)          # outro lote
        self.assertEqual(len(self.client.get("/api/estoque", headers=adm).get_json()), 2)

    def test_rejeita_validade_vencida_e_dados_invalidos(self):
        adm = self.admin()
        pid, fid = self.novo_produto(adm), self.novo_fornecedor(adm)
        self.assertEqual(self.comprar(adm, fid, pid, validade=dias(-1)).status_code, 400)
        self.assertEqual(self.comprar(adm, fid, pid, qtd=0).status_code, 400)
        self.assertEqual(self.comprar(adm, fid, pid, custo=0).status_code, 400)
        self.assertEqual(self.comprar(adm, fid, pid, validade="31/12/2030").status_code, 400)
        self.assertEqual(self.comprar(adm, fid, 999).status_code, 404)
        self.assertEqual(self.comprar(adm, 999, pid).status_code, 404)
        self.assertEqual(self.estoque_total(adm, pid), 0)

    def test_mesmo_lote_com_outra_validade_e_rejeitado_sem_alterar_estoque(self):
        adm = self.admin()
        pid, fid = self.novo_produto(adm), self.novo_fornecedor(adm)
        self.comprar(adm, fid, pid, "L1", validade=dias(100), qtd=10)
        r = self.comprar(adm, fid, pid, "L1", validade=dias(200), qtd=5)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.estoque_total(adm, pid), 10)

    def test_fornecedor_com_compras_nao_pode_ser_removido(self):
        adm = self.admin()
        pid, fid = self.novo_produto(adm), self.novo_fornecedor(adm)
        self.comprar(adm, fid, pid)
        self.assertEqual(self.client.delete(f"/api/fornecedores/{fid}", headers=adm).status_code, 409)


class TestVendas(BaseTest):
    def preparar(self):
        adm = self.admin()
        pid, fid = self.novo_produto(adm, preco=10.0), self.novo_fornecedor(adm)
        _, atend = self.novo_usuario("atendente")
        return adm, atend, pid, fid

    def test_venda_baixa_estoque_e_calcula_total(self):
        adm, atend, pid, fid = self.preparar()
        self.comprar(adm, fid, pid, qtd=10)
        r = self.vender(atend, pid, 3)
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertEqual(r.get_json()["valor_total"], 30.0)
        self.assertEqual(self.estoque_total(adm, pid), 7)

    def test_nao_vende_acima_do_estoque(self):
        adm, atend, pid, fid = self.preparar()
        self.comprar(adm, fid, pid, qtd=5)
        r = self.vender(atend, pid, 6)
        self.assertEqual(r.status_code, 409)
        self.assertIn("disponível: 5", r.get_json()["erro"])
        self.assertEqual(self.estoque_total(adm, pid), 5)

    def test_fefo_vende_primeiro_o_lote_que_vence_antes(self):
        adm, atend, pid, fid = self.preparar()
        self.comprar(adm, fid, pid, "LONGO", validade=dias(400), qtd=10)
        self.comprar(adm, fid, pid, "CURTO", validade=dias(60), qtd=4)
        vid = self.vender(atend, pid, 6).get_json()["id"]
        itens = self.client.get(f"/api/vendas/{vid}", headers=atend).get_json()["itens"]
        self.assertEqual({i["codigo_lote"]: i["quantidade"] for i in itens}, {"CURTO": 4, "LONGO": 2})
        lotes = {l["codigo_lote"]: l["quantidade"] for l in self.client.get("/api/estoque", headers=adm).get_json()}
        self.assertEqual(lotes, {"LONGO": 8})   # lote CURTO zerou e some da lista

    def test_lote_vencido_nao_e_vendido(self):
        adm, atend, pid, fid = self.preparar()
        self.comprar(adm, fid, pid, "VELHO", qtd=10)
        with self.app.app_context():   # simula o tempo passando: o lote vence
            from db import run
            run("UPDATE lotes SET validade=? WHERE codigo_lote='VELHO'", (dias(-1),))
        r = self.vender(atend, pid, 1)
        self.assertEqual(r.status_code, 409)
        prod = [p for p in self.client.get("/api/produtos", headers=adm).get_json() if p["id"] == pid][0]
        self.assertEqual((prod["estoque_total"], prod["estoque_disponivel"]), (10, 0))

    def test_medicamento_com_receita(self):
        adm = self.admin()
        pid, fid = self.novo_produto(adm, "Amoxicilina 500mg", receita=True), self.novo_fornecedor(adm)
        self.comprar(adm, fid, pid, qtd=10)
        _, atend = self.novo_usuario("atendente")
        self.assertEqual(self.vender(atend, pid, 1).status_code, 400)
        self.assertEqual(self.vender(atend, pid, 1, receita_numero="REC-123").status_code, 201)

    def test_validacoes_e_carrinho_com_itens_repetidos(self):
        adm, atend, pid, fid = self.preparar()
        self.comprar(adm, fid, pid, qtd=5)
        self.assertEqual(self.client.post("/api/vendas", headers=atend, json={"itens": []}).status_code, 400)
        self.assertEqual(self.vender(atend, pid, 0).status_code, 400)
        self.assertEqual(self.vender(atend, 999, 1).status_code, 404)
        r = self.client.post("/api/vendas", headers=atend, json={"itens": [
            {"produto_id": pid, "quantidade": 3}, {"produto_id": pid, "quantidade": 3}]})
        self.assertEqual(r.status_code, 409)           # 3+3 > 5: soma os itens repetidos
        self.assertEqual(self.estoque_total(adm, pid), 5)

    def test_venda_com_varios_produtos_e_falha_nao_baixa_nada(self):
        adm, atend, pid, fid = self.preparar()
        p2 = self.novo_produto(adm, "Sabonete Neutro", "higiene", 4.0)
        self.comprar(adm, fid, pid, qtd=5)
        self.comprar(adm, fid, p2, qtd=2)
        ruim = self.client.post("/api/vendas", headers=atend, json={"itens": [
            {"produto_id": pid, "quantidade": 2}, {"produto_id": p2, "quantidade": 5}]})
        self.assertEqual(ruim.status_code, 409)
        self.assertEqual(self.estoque_total(adm, pid), 5)   # nada foi baixado
        ok = self.client.post("/api/vendas", headers=atend, json={"itens": [
            {"produto_id": pid, "quantidade": 2}, {"produto_id": p2, "quantidade": 2}]})
        self.assertEqual(ok.get_json()["valor_total"], 28.0)

    def test_atendente_so_ve_as_proprias_vendas(self):
        adm, atend, pid, fid = self.preparar()
        _, outro = self.novo_usuario("atendente", 2)
        self.comprar(adm, fid, pid, qtd=10)
        vid = self.vender(atend, pid, 1).get_json()["id"]
        self.vender(outro, pid, 1)
        self.assertEqual(len(self.client.get("/api/vendas", headers=atend).get_json()), 1)
        self.assertEqual(len(self.client.get("/api/vendas", headers=adm).get_json()), 2)
        self.assertEqual(self.client.get(f"/api/vendas/{vid}", headers=outro).status_code, 403)


class TestDashboard(BaseTest):
    def test_alertas(self):
        adm = self.admin()
        fid = self.novo_fornecedor(adm)
        baixo = self.novo_produto(adm, "Produto Baixo", minimo=20)
        breve = self.novo_produto(adm, "Produto Vence Breve")
        velho = self.novo_produto(adm, "Produto Vencido")
        self.comprar(adm, fid, baixo, qtd=5)
        self.comprar(adm, fid, breve, validade=dias(10), qtd=50)
        self.comprar(adm, fid, velho, qtd=50)
        with self.app.app_context():
            from db import run
            run("UPDATE lotes SET validade=? WHERE produto_id=?", (dias(-5), velho))
        d = self.client.get("/api/dashboard", headers=adm).get_json()
        self.assertEqual([p["produto"] for p in d["estoque_baixo"]], ["Produto Baixo"])
        self.assertEqual([p["produto"] for p in d["vencendo"]], ["Produto Vence Breve"])
        self.assertEqual([p["produto"] for p in d["vencidos"]], ["Produto Vencido"])
        self.assertEqual(d["total_produtos"], 3)

    def test_vendas_no_dashboard(self):
        adm = self.admin()
        pid, fid = self.novo_produto(adm, preco=10), self.novo_fornecedor(adm)
        self.comprar(adm, fid, pid, qtd=10)
        self.vender(adm, pid, 2)
        d = self.client.get("/api/dashboard", headers=adm).get_json()
        self.assertEqual((d["vendas_hoje"], d["faturamento_30d"]), (20.0, 20.0))
        self.assertEqual(d["vendas_por_dia"][0]["total"], 20.0)
        status = {l["status"] for l in self.client.get("/api/estoque", headers=adm).get_json()}
        self.assertEqual(status, {"ok"})
