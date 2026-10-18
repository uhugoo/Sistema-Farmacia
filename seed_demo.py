"""Carrega dados de exemplo para demonstrar o sistema (rode uma vez: python seed_demo.py).

Cria usuários farmaceutico e atendente, um fornecedor, produtos e lotes — inclusive um lote
que vence em breve, um vencido e um produto abaixo do estoque mínimo, para ver os alertas.
"""
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from app import create_app
from db import q, run


def dias(n):
    return (date.today() + timedelta(days=n)).isoformat()


app = create_app()
with app.app_context():
    if q("SELECT 1 FROM produtos", one=True):
        raise SystemExit("O banco já tem produtos. Apague farmacia.db para recomeçar.")
    for nome, email, perfil in (("Paula Farmaceutica", "farmaceutico@farmacia.com", "farmaceutico"),
                                ("Carlos Atendente", "atendente@farmacia.com", "atendente")):
        run("INSERT INTO usuarios(nome_completo,email,telefone,senha_hash,perfil) VALUES(?,?,?,?,?)",
            (nome, email, "75988887777", generate_password_hash("senha123"), perfil))
    fornecedor = run("INSERT INTO fornecedores(nome,cnpj,telefone) VALUES(?,?,?)",
                     ("Distribuidora Saude Ltda", "11222333000181", "7533334444"))
    produtos = [  # nome, tipo, preço, mínimo, receita, [(lote, validade, qtd)]
        ("Dipirona 500mg", "medicamento", 8.90, 20, 0, [("DIP01", dias(400), 60), ("DIP02", dias(20), 15)]),
        ("Amoxicilina 500mg", "medicamento", 32.50, 10, 1, [("AMX01", dias(300), 40)]),
        ("Sabonete Neutro", "higiene", 3.50, 30, 0, [("SAB01", dias(500), 100)]),
        ("Shampoo Anticaspa", "higiene", 22.00, 15, 0, [("SHA01", dias(250), 8)]),
        ("Hidratante Facial", "cosmetico", 45.90, 5, 0, [("HID01", dias(-10), 12), ("HID02", dias(600), 20)]),
    ]
    for nome, tipo, preco, minimo, receita, lotes in produtos:
        pid = run("INSERT INTO produtos(nome,tipo,preco_venda,estoque_minimo,exige_receita) VALUES(?,?,?,?,?)",
                  (nome, tipo, preco, minimo, receita))
        for codigo, validade, qtd in lotes:
            run("INSERT INTO lotes(produto_id,codigo_lote,validade,quantidade) VALUES(?,?,?,?)", (pid, codigo, validade, qtd))
    print("Dados de exemplo criados.")
    print("Logins: admin@farmacia.com / admin123 | farmaceutico@farmacia.com / senha123 | atendente@farmacia.com / senha123")
