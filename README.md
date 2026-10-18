# FarmaControl - Gestão de Farmácia com Estoque por Lote e Validade

Sistema web para controle de produtos (Medicamentos, Higiene e Cosméticos), compras, vendas e
estoque por lote com data de validade. Stack: **Python + Flask + SQLite + JWT + Chart.js**.

## Como rodar no VS Code
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
flask run --debug
```
Abra http://127.0.0.1:5000 — o banco (`farmacia.db`) é criado automaticamente.

**Login inicial:** `admin@farmacia.com` / `admin123`

**Dados de exemplo (opcional):** `python seed_demo.py` cria produtos, lotes (um vencido, um perto de vencer),
um fornecedor e os usuários `farmaceutico@farmacia.com` e `atendente@farmacia.com` (senha `senha123`).
Para recomeçar do zero, pare o sistema e apague o arquivo `farmacia.db`.

## Perfis
| Perfil | Pode |
|---|---|
| admin | tudo, inclusive cadastrar e remover usuários |
| farmaceutico | produtos, fornecedores, compras, vendas, estoque e visão geral |
| atendente | registrar vendas (vê só as próprias) e consultar o estoque |

## Regras de negócio
- **Compra** cria um lote (com validade) ou soma em um lote existente; atualiza o estoque.
- **Venda** baixa o estoque pelo método **FEFO**: sai primeiro o lote que vence antes.
- Não vende acima do estoque e **não vende lote vencido**.
- Não aceita compra com validade vencida; o mesmo lote não pode ter duas validades.
- Medicamento marcado "exige receita" só vende com o número da receita.
- Produto, fornecedor ou usuário com movimentações não pode ser removido.
- Alertas: estoque abaixo do mínimo, lotes que vencem em até 30 dias e lotes vencidos.
- Vendas e compras são gravadas de forma atômica: se um item falha, nada é baixado.

## Estrutura
```
app.py  db.py  auth.py  validators.py  seed_demo.py
routes/     usuarios, produtos, compras (e fornecedores), vendas, estoque (e dashboard)
services/   estoque.py  -> regra FEFO e status da validade
templates/  index.html      static/  style.css, app.js
tests/      unit/  integration/  selenium/
```

## Testes
```bash
pytest tests/unit tests/integration -v     # não precisam do servidor
pytest tests/selenium -v                   # rode `flask run` em outro terminal antes
```
Sem pytest: `python -m unittest discover -s tests -t .`

## Relação com a atividade avaliativa
| Item | Onde está |
|---|---|
| 1 Login | `POST /api/auth/login` (JWT) e tela de login |
| 2 Usuário Admin | perfil `admin` e decorator `@auth("admin")` |
| 3 / 4 Cadastro / remoção de usuário | `routes/usuarios.py` (nome completo, ID, e-mail, telefone) |
| 5 / 6 Cadastro / remoção de produtos (3 tipos) | `routes/produtos.py` |
| 7 Compra e venda | `routes/compras.py` e `routes/vendas.py` |
| 8 Atualização de estoque | lotes atualizados a cada compra e venda |
| 9 Unitário / integração | `tests/unit`, `tests/integration` |
| 10-12 Sistema, aceitação, alfa/beta | fluxo completo: fornecedor -> compra -> venda -> estoque/alertas |
| 13 Regressão | reexecutar toda a suíte após cada correção |
| 14 Automação Selenium | `tests/selenium/test_ui.py` |
