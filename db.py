import sqlite3
from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome_completo TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  telefone TEXT NOT NULL,
  senha_hash TEXT NOT NULL,
  perfil TEXT NOT NULL CHECK(perfil IN ('admin','farmaceutico','atendente')),
  ativo INTEGER NOT NULL DEFAULT 1,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS fornecedores(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL, cnpj TEXT NOT NULL UNIQUE, telefone TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS produtos(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL UNIQUE,
  tipo TEXT NOT NULL CHECK(tipo IN ('medicamento','higiene','cosmetico')),
  preco_venda REAL NOT NULL,
  estoque_minimo INTEGER NOT NULL DEFAULT 0,
  exige_receita INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS lotes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
  codigo_lote TEXT NOT NULL,
  validade TEXT NOT NULL,
  quantidade INTEGER NOT NULL CHECK(quantidade >= 0),
  UNIQUE(produto_id, codigo_lote));
CREATE TABLE IF NOT EXISTS compras(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE RESTRICT,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
  data TEXT NOT NULL, valor_total REAL NOT NULL);
CREATE TABLE IF NOT EXISTS itens_compra(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  compra_id INTEGER NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
  produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
  lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE RESTRICT,
  quantidade INTEGER NOT NULL, custo_unitario REAL NOT NULL);
CREATE TABLE IF NOT EXISTS vendas(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
  data TEXT NOT NULL, valor_total REAL NOT NULL, receita_numero TEXT);
CREATE TABLE IF NOT EXISTS itens_venda(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  venda_id INTEGER NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
  produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
  lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE RESTRICT,
  quantidade INTEGER NOT NULL, preco_unitario REAL NOT NULL);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def q(sql, args=(), one=False):
    rows = [dict(r) for r in get_db().execute(sql, args).fetchall()]
    if one:
        return rows[0] if rows else None
    return rows


def run(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def init_db():
    """Cria as tabelas e o usuário admin inicial."""
    get_db().executescript(SCHEMA)
    if not q("SELECT 1 FROM usuarios WHERE perfil='admin'", one=True):
        run("INSERT INTO usuarios(nome_completo,email,telefone,senha_hash,perfil) VALUES(?,?,?,?,?)",
            ("Administrador Geral", "admin@farmacia.com", "75999999999",
             generate_password_hash("admin123"), "admin"))
