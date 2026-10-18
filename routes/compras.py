import sqlite3
from datetime import date, datetime
from flask import Blueprint, g, jsonify, request
import validators as v
from auth import auth, erro
from db import get_db, q, run

bp = Blueprint("compras", __name__, url_prefix="/api")


# ---------- Fornecedores ----------
@bp.get("/fornecedores")
@auth("admin", "farmaceutico")
def listar_fornecedores():
    return jsonify(q("SELECT * FROM fornecedores ORDER BY nome"))


@bp.post("/fornecedores")
@auth("admin", "farmaceutico")
def criar_fornecedor():
    d = request.get_json(silent=True) or {}
    nome = (d.get("nome") or "").strip()
    if len(nome) < 2:
        return erro("Informe o nome do fornecedor")
    msg = v.cnpj(d.get("cnpj")) or v.telefone(d.get("telefone"))
    if msg:
        return erro(msg)
    digitos = "".join(c for c in d["cnpj"] if c.isdigit())
    if q("SELECT 1 FROM fornecedores WHERE cnpj=?", (digitos,), one=True):
        return erro("CNPJ já cadastrado", 409)
    return jsonify({"id": run("INSERT INTO fornecedores(nome,cnpj,telefone) VALUES(?,?,?)",
                              (nome, digitos, d["telefone"]))}), 201


@bp.delete("/fornecedores/<int:fid>")
@auth("admin", "farmaceutico")
def remover_fornecedor(fid):
    if not q("SELECT 1 FROM fornecedores WHERE id=?", (fid,), one=True):
        return erro("Fornecedor não encontrado", 404)
    try:
        run("DELETE FROM fornecedores WHERE id=?", (fid,))
    except sqlite3.IntegrityError:
        return erro("Fornecedor possui compras registradas e não pode ser removido", 409)
    return jsonify({"ok": True})


# ---------- Compras (entrada de estoque) ----------
@bp.post("/compras")
@auth("admin", "farmaceutico")
def comprar():
    """Registra a compra e cria/soma os lotes (atualização de estoque)."""
    d = request.get_json(silent=True) or {}
    if not q("SELECT 1 FROM fornecedores WHERE id=?", (d.get("fornecedor_id"),), one=True):
        return erro("Fornecedor não encontrado", 404)
    itens = d.get("itens") or []
    if not itens:
        return erro("A compra precisa de pelo menos um item")
    for it in itens:
        if not q("SELECT 1 FROM produtos WHERE id=?", (it.get("produto_id"),), one=True):
            return erro("Produto não encontrado", 404)
        if not (it.get("codigo_lote") or "").strip():
            return erro("Informe o código do lote")
        msg = (v.inteiro_positivo(it.get("quantidade"), "Quantidade") or
               v.preco(it.get("custo_unitario"), "Custo unitário") or
               v.validade_nao_vencida(it.get("validade")))
        if msg:
            return erro(msg)

    db = get_db()
    total = round(sum(i["quantidade"] * i["custo_unitario"] for i in itens), 2)
    try:
        cid = db.execute("INSERT INTO compras(fornecedor_id,usuario_id,data,valor_total) VALUES(?,?,?,?)",
                         (d["fornecedor_id"], g.user["id"], datetime.now().isoformat(timespec="seconds"), total)).lastrowid
        for it in itens:
            codigo = it["codigo_lote"].strip()
            lote = db.execute("SELECT id,validade FROM lotes WHERE produto_id=? AND codigo_lote=?",
                              (it["produto_id"], codigo)).fetchone()
            if lote and lote["validade"] != it["validade"]:
                raise ValueError(f"O lote {codigo} já existe com outra validade ({lote['validade']})")
            if lote:
                lote_id = lote["id"]
                db.execute("UPDATE lotes SET quantidade=quantidade+? WHERE id=?", (it["quantidade"], lote_id))
            else:
                lote_id = db.execute("INSERT INTO lotes(produto_id,codigo_lote,validade,quantidade) VALUES(?,?,?,?)",
                                     (it["produto_id"], codigo, it["validade"], it["quantidade"])).lastrowid
            db.execute("INSERT INTO itens_compra(compra_id,produto_id,lote_id,quantidade,custo_unitario) VALUES(?,?,?,?,?)",
                       (cid, it["produto_id"], lote_id, it["quantidade"], it["custo_unitario"]))
        db.commit()
    except ValueError as e:
        db.rollback()
        return erro(str(e))
    except Exception:
        db.rollback()
        raise
    return jsonify({"id": cid, "valor_total": total}), 201


@bp.get("/compras")
@auth("admin", "farmaceutico")
def listar_compras():
    return jsonify(q("SELECT c.id,c.data,c.valor_total,f.nome AS fornecedor,u.nome_completo AS usuario,"
                     "(SELECT SUM(quantidade) FROM itens_compra WHERE compra_id=c.id) AS itens "
                     "FROM compras c JOIN fornecedores f ON f.id=c.fornecedor_id "
                     "JOIN usuarios u ON u.id=c.usuario_id ORDER BY c.id DESC"))
