import sqlite3
from datetime import date
from flask import Blueprint, jsonify, request
import validators as v
from auth import auth, erro
from db import q, run

bp = Blueprint("produtos", __name__, url_prefix="/api")


@bp.get("/produtos")
@auth()
def listar():
    sql = ("SELECT p.id,p.nome,p.tipo,p.preco_venda,p.estoque_minimo,p.exige_receita,"
           "COALESCE((SELECT SUM(quantidade) FROM lotes WHERE produto_id=p.id),0) AS estoque_total,"
           "COALESCE((SELECT SUM(quantidade) FROM lotes WHERE produto_id=p.id AND validade>=?),0) AS estoque_disponivel "
           "FROM produtos p WHERE p.nome LIKE ?")
    args = [date.today().isoformat(), f"%{request.args.get('q', '').strip()}%"]
    if request.args.get("tipo"):
        sql += " AND p.tipo=?"
        args.append(request.args["tipo"])
    return jsonify(q(sql + " ORDER BY p.nome", args))


def validar(d):
    if len((d.get("nome") or "").strip()) < 2:
        return "Informe o nome do produto"
    if d.get("tipo") not in v.TIPOS_PRODUTO:
        return "Tipo inválido (medicamento, higiene ou cosmetico)"
    minimo = d.get("estoque_minimo", 0)
    return v.preco(d.get("preco_venda"), "Preço") or v.inteiro_nao_negativo(minimo, "Estoque mínimo")


@bp.post("/produtos")
@auth("admin", "farmaceutico")
def criar():
    d = request.get_json(silent=True) or {}
    msg = validar(d)
    if msg:
        return erro(msg)
    nome = d["nome"].strip()
    if q("SELECT 1 FROM produtos WHERE nome=?", (nome,), one=True):
        return erro("Produto já cadastrado", 409)
    pid = run("INSERT INTO produtos(nome,tipo,preco_venda,estoque_minimo,exige_receita) VALUES(?,?,?,?,?)",
              (nome, d["tipo"], d["preco_venda"], d.get("estoque_minimo", 0), 1 if d.get("exige_receita") else 0))
    return jsonify({"id": pid}), 201


@bp.put("/produtos/<int:pid>")
@auth("admin", "farmaceutico")
def editar(pid):
    d = request.get_json(silent=True) or {}
    if not q("SELECT 1 FROM produtos WHERE id=?", (pid,), one=True):
        return erro("Produto não encontrado", 404)
    msg = validar(d)
    if msg:
        return erro(msg)
    try:
        run("UPDATE produtos SET nome=?,tipo=?,preco_venda=?,estoque_minimo=?,exige_receita=? WHERE id=?",
            (d["nome"].strip(), d["tipo"], d["preco_venda"], d.get("estoque_minimo", 0),
             1 if d.get("exige_receita") else 0, pid))
    except sqlite3.IntegrityError:
        return erro("Já existe produto com esse nome", 409)
    return jsonify({"ok": True})


@bp.delete("/produtos/<int:pid>")
@auth("admin", "farmaceutico")
def remover(pid):
    if not q("SELECT 1 FROM produtos WHERE id=?", (pid,), one=True):
        return erro("Produto não encontrado", 404)
    movimentado = (q("SELECT 1 FROM itens_compra WHERE produto_id=?", (pid,), one=True) or
                   q("SELECT 1 FROM itens_venda WHERE produto_id=?", (pid,), one=True))
    if movimentado:
        return erro("Produto possui compras ou vendas registradas e não pode ser removido", 409)
    try:
        run("DELETE FROM produtos WHERE id=?", (pid,))
    except sqlite3.IntegrityError:
        return erro("Produto possui vínculos e não pode ser removido", 409)
    return jsonify({"ok": True})
