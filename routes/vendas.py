from datetime import datetime, date
from flask import Blueprint, g, jsonify, request
import validators as v
from auth import auth, erro
from db import get_db, q
from services.estoque import EstoqueInsuficiente, escolher_lotes

bp = Blueprint("vendas", __name__, url_prefix="/api")


@bp.post("/vendas")
@auth()
def vender():
    """Registra a venda, baixa o estoque pelos lotes que vencem primeiro (FEFO)."""
    d = request.get_json(silent=True) or {}
    itens = d.get("itens") or []
    if not itens:
        return erro("O carrinho está vazio")

    pedido = {}  # produto_id -> quantidade total (junta itens repetidos)
    for it in itens:
        msg = v.inteiro_positivo(it.get("produto_id"), "Produto") or v.inteiro_positivo(it.get("quantidade"), "Quantidade")
        if msg:
            return erro(msg)
        pedido[it["produto_id"]] = pedido.get(it["produto_id"], 0) + it["quantidade"]

    receita = (d.get("receita_numero") or "").strip()
    hoje = date.today()
    plano, total = [], 0.0
    for pid, qtd in pedido.items():
        p = q("SELECT * FROM produtos WHERE id=?", (pid,), one=True)
        if not p:
            return erro("Produto não encontrado", 404)
        if p["exige_receita"] and not receita:
            return erro(f"{p['nome']} exige o número da receita")
        lotes = q("SELECT id,validade,quantidade FROM lotes WHERE produto_id=?", (pid,))
        try:
            usados = escolher_lotes(lotes, qtd, hoje)
        except EstoqueInsuficiente as e:
            return erro(f"Estoque insuficiente de {p['nome']} (disponível: {e.disponivel})", 409)
        plano.append((p, usados))
        total += qtd * p["preco_venda"]

    db = get_db()
    try:
        vid = db.execute("INSERT INTO vendas(usuario_id,data,valor_total,receita_numero) VALUES(?,?,?,?)",
                         (g.user["id"], datetime.now().isoformat(timespec="seconds"), round(total, 2), receita or None)).lastrowid
        for p, usados in plano:
            for lote_id, usada in usados:
                db.execute("INSERT INTO itens_venda(venda_id,produto_id,lote_id,quantidade,preco_unitario) VALUES(?,?,?,?,?)",
                           (vid, p["id"], lote_id, usada, p["preco_venda"]))
                db.execute("UPDATE lotes SET quantidade=quantidade-? WHERE id=?", (usada, lote_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return jsonify({"id": vid, "valor_total": round(total, 2)}), 201


@bp.get("/vendas")
@auth()
def listar():
    sql = ("SELECT v.id,v.data,v.valor_total,v.receita_numero,u.nome_completo AS vendedor,"
           "(SELECT SUM(quantidade) FROM itens_venda WHERE venda_id=v.id) AS itens "
           "FROM vendas v JOIN usuarios u ON u.id=v.usuario_id")
    args = ()
    if g.user["perfil"] == "atendente":
        sql += " WHERE v.usuario_id=?"
        args = (g.user["id"],)
    return jsonify(q(sql + " ORDER BY v.id DESC", args))


@bp.get("/vendas/<int:vid>")
@auth()
def detalhe(vid):
    venda = q("SELECT v.*,u.nome_completo AS vendedor FROM vendas v JOIN usuarios u ON u.id=v.usuario_id WHERE v.id=?",
              (vid,), one=True)
    if not venda:
        return erro("Venda não encontrada", 404)
    if g.user["perfil"] == "atendente" and venda["usuario_id"] != g.user["id"]:
        return erro("Acesso negado", 403)
    venda["itens"] = q("SELECT p.nome,l.codigo_lote,l.validade,i.quantidade,i.preco_unitario FROM itens_venda i "
                       "JOIN produtos p ON p.id=i.produto_id JOIN lotes l ON l.id=i.lote_id WHERE i.venda_id=?", (vid,))
    return jsonify(venda)
