import os
from flask import Flask, jsonify, render_template
from db import close_db, init_db


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = os.path.join(app.root_path, "farmacia.db")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao-0123456789")
    if config:
        app.config.update(config)

    app.teardown_appcontext(close_db)

    from routes import usuarios, produtos, compras, vendas, estoque
    for modulo in (usuarios, produtos, compras, vendas, estoque):
        app.register_blueprint(modulo.bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(404)
    def nao_encontrado(_):
        return jsonify({"erro": "Rota não encontrada"}), 404

    with app.app_context():
        init_db()
    return app


if __name__ == "__main__":
    create_app().run(debug=True)
