let token = localStorage.getItem('token'), me = JSON.parse(localStorage.getItem('me') || 'null');
let grafico = null, PRODUTOS = [], CARRINHO = [];
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const brl = n => 'R$ ' + Number(n || 0).toFixed(2).replace('.', ',');
const dataBr = iso => iso ? iso.slice(0, 10).split('-').reverse().join('/') : '';
const ABAS = {
  admin: ['dashboard','produtos','fornecedores','compras','vendas','estoque','usuarios'],
  farmaceutico: ['dashboard','produtos','fornecedores','compras','vendas','estoque'],
  atendente: ['vendas','estoque']
};
const NOMES = {dashboard:'Visão geral',produtos:'Produtos',fornecedores:'Fornecedores',compras:'Compras',vendas:'Vendas',estoque:'Estoque',usuarios:'Usuários'};
const CARREGAR = {dashboard:carregarDashboard,produtos:carregarProdutos,fornecedores:carregarFornecedores,compras:carregarCompras,vendas:carregarVendas,estoque:carregarEstoque,usuarios:carregarUsuarios};
const PODE_EDITAR = () => me.perfil === 'admin' || me.perfil === 'farmaceutico';

function aviso(txt, erro) {
  const m = $('msg'); m.textContent = txt; m.className = erro ? 'err' : 'ok';
  setTimeout(() => m.className = 'oculto', 3500);
}
async function api(metodo, url, corpo) {
  const r = await fetch(url, {method: metodo, headers: {'Content-Type':'application/json', ...(token ? {Authorization:'Bearer '+token} : {})}, body: corpo ? JSON.stringify(corpo) : undefined});
  const d = await r.json().catch(() => ({}));
  if (r.status === 401 && token) { sair(); }
  if (!r.ok) throw new Error(d.erro || 'Erro ' + r.status);
  return d;
}
const tentar = fn => async (...a) => { try { await fn(...a); } catch (e) { aviso(e.message, true); } };

// ---- Telefone (DDD separado) e campos numéricos
function telefoneCompleto(ddd, numero) {
  ddd = ddd.replace(/\D/g, ''); numero = numero.replace(/\D/g, '');
  if (ddd.length !== 2) throw new Error('Informe o DDD com 2 dígitos');
  if (numero.length < 8 || numero.length > 9) throw new Error('Telefone deve ter 8 ou 9 dígitos');
  return ddd + numero;
}
document.addEventListener('input', e => { if (e.target.classList.contains('so-numeros')) e.target.value = e.target.value.replace(/\D/g, ''); });
const fmtTel = t => t && t.length >= 10 ? `(${t.slice(0,2)}) ${t.slice(2, t.length - 4)}-${t.slice(-4)}` : t;
const fmtCnpj = c => c && c.length === 14 ? c.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5') : c;

// ---- Login
async function entrar() {
  $('msg-login').textContent = '';
  try {
    const d = await api('POST', '/api/auth/login', {email: $('email').value, senha: $('senha').value});
    token = d.token; me = d;
    localStorage.setItem('token', token); localStorage.setItem('me', JSON.stringify(me));
    iniciar();
  } catch (e) { $('msg-login').textContent = e.message; }
}
function sair() {
  token = null; me = null; localStorage.clear(); CARRINHO = [];
  $('painel').classList.add('oculto'); $('btn-sair').classList.add('oculto');
  $('tela-login').classList.remove('oculto'); $('usuario-logado').textContent = '';
}
function iniciar() {
  $('tela-login').classList.add('oculto'); $('painel').classList.remove('oculto'); $('btn-sair').classList.remove('oculto');
  $('usuario-logado').textContent = `${me.nome} (${me.perfil})`;
  $('form-produto').classList.toggle('oculto', !PODE_EDITAR());
  $('menu').innerHTML = ABAS[me.perfil].map(a => `<button id="menu-${a}" onclick="abrir('${a}')">${NOMES[a]}</button>`).join('');
  abrir(ABAS[me.perfil][0]);
}
const abrir = tentar(async aba => {
  document.querySelectorAll('.aba').forEach(e => e.classList.add('oculto'));
  $('aba-' + aba).classList.remove('oculto');
  document.querySelectorAll('#menu button').forEach(b => b.classList.toggle('ativa', b.id === 'menu-' + aba));
  await CARREGAR[aba]();
});

// ---- Dashboard
async function carregarDashboard() {
  const d = await api('GET', '/api/dashboard');
  $('i-produtos').textContent = d.total_produtos;
  $('i-hoje').textContent = brl(d.vendas_hoje);
  $('i-mes').textContent = brl(d.faturamento_30d);
  const lista = (id, itens, fmt) => $(id).innerHTML = itens.map(i => `<li>${fmt(i)}</li>`).join('') || '<li>Nenhum 👍</li>';
  lista('al-baixo', d.estoque_baixo, i => `${esc(i.produto)}: ${i.disponivel} (mín. ${i.estoque_minimo})`);
  lista('al-vencendo', d.vencendo, i => `${esc(i.produto)} - lote ${esc(i.codigo_lote)}: ${i.quantidade} un. até ${dataBr(i.validade)}`);
  lista('al-vencidos', d.vencidos, i => `${esc(i.produto)} - lote ${esc(i.codigo_lote)}: ${i.quantidade} un. (venceu em ${dataBr(i.validade)})`);
  if (grafico) grafico.destroy();
  grafico = new Chart($('grafico-vendas'), {type: 'bar', data: {labels: d.vendas_por_dia.map(v => dataBr(v.dia)),
    datasets: [{label: 'Vendas (R$)', data: d.vendas_por_dia.map(v => v.total), backgroundColor: '#198754'}]}});
}

// ---- Produtos
async function carregarProdutos() {
  PRODUTOS = await api('GET', `/api/produtos?q=${encodeURIComponent($('p-busca').value)}&tipo=${$('p-filtro').value}`);
  $('tb-produtos').innerHTML = PRODUTOS.map(p => `<tr><td>${esc(p.nome)}</td><td>${p.tipo}</td><td>${brl(p.preco_venda)}</td>
    <td>${p.estoque_total}${p.estoque_disponivel !== p.estoque_total ? ` <small>(${p.estoque_disponivel} válidos)</small>` : ''}</td>
    <td>${p.estoque_minimo}</td><td>${p.exige_receita ? 'sim' : '-'}</td>
    <td>${PODE_EDITAR() ? `<button class="del" onclick="removerProduto(${p.id})">Remover</button>` : ''}</td></tr>`).join('');
}
const addProduto = tentar(async () => {
  await api('POST', '/api/produtos', {nome: $('p-nome').value, tipo: $('p-tipo').value, preco_venda: parseFloat($('p-preco').value),
    estoque_minimo: $('p-minimo').value === '' ? 0 : parseInt($('p-minimo').value), exige_receita: $('p-receita').checked});
  ['p-nome','p-preco','p-minimo'].forEach(i => $(i).value = ''); $('p-receita').checked = false;
  aviso('Produto cadastrado'); carregarProdutos();
});
const removerProduto = tentar(async id => { if (!confirm('Remover produto?')) return; await api('DELETE', '/api/produtos/' + id); aviso('Produto removido'); carregarProdutos(); });

// ---- Fornecedores
async function carregarFornecedores() {
  const fs = await api('GET', '/api/fornecedores');
  $('tb-fornecedores').innerHTML = fs.map(f => `<tr><td>${esc(f.nome)}</td><td>${fmtCnpj(f.cnpj)}</td><td>${fmtTel(f.telefone)}</td>
    <td><button class="del" onclick="removerFornecedor(${f.id})">Remover</button></td></tr>`).join('');
}
const addFornecedor = tentar(async () => {
  await api('POST', '/api/fornecedores', {nome: $('f-nome').value, cnpj: $('f-cnpj').value, telefone: telefoneCompleto($('f-ddd').value, $('f-tel').value)});
  ['f-nome','f-cnpj','f-ddd','f-tel'].forEach(i => $(i).value = ''); aviso('Fornecedor cadastrado'); carregarFornecedores();
});
const removerFornecedor = tentar(async id => { if (!confirm('Remover fornecedor?')) return; await api('DELETE', '/api/fornecedores/' + id); aviso('Fornecedor removido'); carregarFornecedores(); });

// ---- Compras
async function carregarCompras() {
  const [fs, ps, cs] = await Promise.all([api('GET', '/api/fornecedores'), api('GET', '/api/produtos'), api('GET', '/api/compras')]);
  PRODUTOS = ps;
  $('c-fornecedor').innerHTML = fs.map(f => `<option value="${f.id}">${esc(f.nome)}</option>`).join('');
  $('c-itens').innerHTML = ''; addLinhaCompra();
  $('tb-compras').innerHTML = cs.map(c => `<tr><td>${c.data.replace('T', ' ')}</td><td>${esc(c.fornecedor)}</td><td>${c.itens}</td><td>${brl(c.valor_total)}</td><td>${esc(c.usuario)}</td></tr>`).join('');
}
function addLinhaCompra() {
  const d = document.createElement('div'); d.className = 'linha linha-compra';
  d.innerHTML = `<select style="min-width:200px">${PRODUTOS.map(p => `<option value="${p.id}">${esc(p.nome)}</option>`).join('')}</select>
    <input placeholder="Lote" style="width:100px"><input type="date" title="Validade"><input type="number" min="1" placeholder="Qtd" style="width:80px"><input type="number" min="0" step="0.01" placeholder="Custo un." style="width:100px">`;
  $('c-itens').appendChild(d);
}
const registrarCompra = tentar(async () => {
  const itens = [...document.querySelectorAll('.linha-compra')].map(l => { const [p, lote, val, qtd, custo] = l.querySelectorAll('select,input');
    return {produto_id: +p.value, codigo_lote: lote.value, validade: val.value, quantidade: parseInt(qtd.value), custo_unitario: parseFloat(custo.value)}; });
  await api('POST', '/api/compras', {fornecedor_id: +$('c-fornecedor').value, itens});
  aviso('Compra registrada! Estoque atualizado.'); carregarCompras();
});

// ---- Vendas (PDV)
async function carregarVendas() {
  PRODUTOS = await api('GET', '/api/produtos');
  $('v-produto').innerHTML = PRODUTOS.map(p => `<option value="${p.id}">${esc(p.nome)} - ${brl(p.preco_venda)} (${p.estoque_disponivel} disp.)</option>`).join('');
  renderCarrinho();
  const vs = await api('GET', '/api/vendas');
  $('tb-vendas').innerHTML = vs.map(v => `<tr><td>${v.id}</td><td>${v.data.replace('T', ' ')}</td><td>${v.itens}</td><td>${brl(v.valor_total)}</td><td>${esc(v.vendedor)}</td></tr>`).join('');
}
function addCarrinho() {
  const p = PRODUTOS.find(x => x.id == $('v-produto').value), qtd = parseInt($('v-qtd').value);
  if (!p) return aviso('Selecione um produto', true);
  if (!(qtd > 0)) return aviso('Quantidade deve ser maior que zero', true);
  const item = CARRINHO.find(i => i.produto_id === p.id);
  if (item) item.quantidade += qtd; else CARRINHO.push({produto_id: p.id, nome: p.nome, quantidade: qtd, preco: p.preco_venda});
  $('v-qtd').value = 1; renderCarrinho();
}
function renderCarrinho() {
  $('tb-carrinho').innerHTML = CARRINHO.map((i, n) => `<tr><td>${esc(i.nome)}</td><td>${i.quantidade}</td><td>${brl(i.preco)}</td><td>${brl(i.quantidade * i.preco)}</td>
    <td><button class="del" onclick="tirarDoCarrinho(${n})">x</button></td></tr>`).join('') || '<tr><td colspan="5">Carrinho vazio</td></tr>';
  $('v-total').textContent = brl(CARRINHO.reduce((s, i) => s + i.quantidade * i.preco, 0));
}
function tirarDoCarrinho(n) { CARRINHO.splice(n, 1); renderCarrinho(); }
const finalizarVenda = tentar(async () => {
  const r = await api('POST', '/api/vendas', {itens: CARRINHO.map(i => ({produto_id: i.produto_id, quantidade: i.quantidade})), receita_numero: $('v-receita').value});
  CARRINHO = []; $('v-receita').value = '';
  aviso(`Venda #${r.id} finalizada: ${brl(r.valor_total)}`); carregarVendas();
});

// ---- Estoque
const ROTULO = {ok: 'ok', vence_em_breve: 'vence em breve', vencido: 'vencido'};
async function carregarEstoque() {
  const ls = await api('GET', `/api/estoque?q=${encodeURIComponent($('s-busca').value)}&status=${$('s-filtro').value}`);
  $('tb-estoque').innerHTML = ls.map(l => `<tr><td>${esc(l.produto)}</td><td>${l.tipo}</td><td>${esc(l.codigo_lote)}</td><td>${dataBr(l.validade)}</td><td>${l.quantidade}</td>
    <td><span class="badge ${l.status}">${ROTULO[l.status]}</span></td></tr>`).join('') || '<tr><td colspan="6">Nenhum lote encontrado</td></tr>';
}

// ---- Usuários (admin)
async function carregarUsuarios() {
  const us = await api('GET', '/api/usuarios?q=' + encodeURIComponent($('u-busca').value));
  $('tb-usuarios').innerHTML = us.map(u => `<tr><td>${u.id}</td><td>${esc(u.nome_completo)}</td><td>${esc(u.email)}</td><td>${fmtTel(u.telefone)}</td><td>${u.perfil}</td>
    <td>${u.id !== me.id ? `<button class="del" onclick="removerUsuario(${u.id})">Remover</button>` : ''}</td></tr>`).join('');
}
const addUsuario = tentar(async () => {
  await api('POST', '/api/usuarios', {nome_completo: $('u-nome').value, email: $('u-email').value, telefone: telefoneCompleto($('u-ddd').value, $('u-tel').value), senha: $('u-senha').value, perfil: $('u-perfil').value});
  ['u-nome','u-email','u-ddd','u-tel','u-senha'].forEach(i => $(i).value = ''); aviso('Usuário cadastrado'); carregarUsuarios();
});
const removerUsuario = tentar(async id => { if (!confirm('Remover usuário?')) return; await api('DELETE', '/api/usuarios/' + id); aviso('Usuário removido'); carregarUsuarios(); });

if (token && me) iniciar();
$('senha').addEventListener('keydown', e => { if (e.key === 'Enter') entrar(); });
