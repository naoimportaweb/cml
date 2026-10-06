<?php
// Organograma no site publico (somente leitura).
//
// ⚠️ O LAYOUT ABAIXO E UMA SEGUNDA IMPLEMENTACAO do que esta em
// app/classlib/organization_chart/organization_chart_item.py. O desktop calcula a arvore no
// cliente e o banco guarda so o `x`, entao nao ha geometria para reusar aqui. Decisao do dono
// (2026-10-06), com o custo conhecido: mudou o layout ou o desenho la, tem de mudar aqui.
// Mantive os MESMOS nomes e as mesmas constantes do Python de proposito, para a comparacao
// lado a lado ser possivel.

require_once dirname(dirname(__DIR__)) . "/api/mysql.php";

$id     = isset($_GET["id"])     ? $_GET["id"]     : "";
$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CML — organograma</title>
  <link rel="stylesheet" href="../../public/cml.css">
<style>
.topo { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; }
.barra { display:flex; gap:6px; align-items:center; margin:10px 0; flex-wrap:wrap; }
.barra button { padding:6px 12px; }
.tela { border:1px solid var(--border); border-radius:8px; overflow:auto; background:#fff;
        max-height:calc(100vh - 190px); }
#canvas { display:block; }
.vazio { padding:30px; color:var(--muted); }
</style>
</head>
<body>
<div class="wrap">
  <header class="topo">
    <h1 id="titulo">Organograma</h1>
    <span class="tag" id="sub"></span>
  </header>
  <p><a href="../relationship/index.php?domain=<?php echo urlencode($domain); ?>">← voltar à lista</a></p>
  <div class="barra">
    <button onclick="zoom(1.15)">Zoom +</button>
    <button onclick="zoom(1/1.15)">Zoom −</button>
    <button onclick="ajustar()">Ajustar à janela</button>
    <button onclick="zoomar(1)">100%</button>
    <span class="tag" id="aviso"></span>
  </div>
  <div class="tela"><canvas id="canvas" width="100" height="100"></canvas></div>
</div>

<script>
// ---------------------------------------------------------------- constantes
// Iguais as do organization_chart_item.py. Mudou la, muda aqui.
var ESPACO_IRMAO   = 28;
var ESPACO_NIVEL   = 58;
var MARGEM_CAIXA   = 10;
var ALTURA_TITULO  = 22;
var ALTURA_LINHA   = 15;
var LARGURA_MINIMA = 120;
var LARGURA_MAXIMA = 260;

var COR_BORDA      = "#3c4655";
var COR_FUNDO      = "#ffffff";
var COR_FUNDO_RAIZ = "#e8eef8";
var COR_CONECTOR   = "#6e7a8c";
var COR_SEPARADOR  = "#cdd4de";
var COR_SECUNDARIO = "#46505f";

var FONTE = "13px 'DejaVu Sans Mono', monospace";
var FONTE_NEGRITO = "bold 13px 'DejaVu Sans Mono', monospace";

var cv = document.getElementById("canvas");
var ctx = cv.getContext("2d");
var raiz = null, escala = 1;

// ---------------------------------------------------------------- medida
function quebrar(texto, largura, fonte) {
  // Quebra por LARGURA medida, nao por contagem de caracteres: com fonte proporcional,
  // contar caractere nao tem relacao com o que cabe.
  ctx.font = fonte;
  var palavras = String(texto || "").split(/\s+/).filter(function(p){ return p !== ""; });
  if (palavras.length === 0) { return []; }
  var linhas = [], atual = "";
  for (var i = 0; i < palavras.length; i++) {
    var tentativa = atual === "" ? palavras[i] : atual + " " + palavras[i];
    if (ctx.measureText(tentativa).width <= largura || atual === "") { atual = tentativa; }
    else { linhas.push(atual); atual = palavras[i]; }
  }
  if (atual !== "") { linhas.push(atual); }
  return linhas;
}

function medir(item) {
  ctx.font = FONTE_NEGRITO;
  var largura = Math.max(LARGURA_MINIMA,
                Math.min(LARGURA_MAXIMA, ctx.measureText(item.texto || "").width + MARGEM_CAIXA * 2));
  item.linhas_titulo = quebrar(item.texto, largura - MARGEM_CAIXA * 2, FONTE_NEGRITO);
  if (item.linhas_titulo.length === 0) { item.linhas_titulo = [""]; }
  item.linhas_nomes = [];
  for (var i = 0; i < item.entidades.length; i++) {
    var nome = item.entidades[i].nome;
    if (!nome) { continue; }
    item.linhas_nomes = item.linhas_nomes.concat(quebrar(nome, largura - MARGEM_CAIXA * 2, FONTE));
  }
  item.w = Math.round(largura);
  item.h = Math.round(MARGEM_CAIXA + ALTURA_TITULO * item.linhas_titulo.length
           + (item.linhas_nomes.length > 0 ? 6 + ALTURA_LINHA * item.linhas_nomes.length : 0)
           + MARGEM_CAIXA);
  for (var k = 0; k < item.filhos.length; k++) { medir(item.filhos[k]); }
}

// ---------------------------------------------------------------- layout
function deslocar(item, dx) {
  item.x += dx;
  for (var i = 0; i < item.filhos.length; i++) { deslocar(item.filhos[i], dx); }
}

function registrar(item, limites) {
  var atual = limites[item.nivel] || 0;
  limites[item.nivel] = Math.max(atual, item.x + item.w + ESPACO_IRMAO);
  for (var i = 0; i < item.filhos.length; i++) { registrar(item.filhos[i], limites); }
}

function posicionar(item, limites) {
  // `limites` guarda o proximo x livre POR NIVEL. Tem de ser por nivel: um limite global
  // empurraria todo mundo a cada caixa, e um limite que nao acompanha o nivel deixa duas
  // irmas encostando -- foi o defeito que apareceu no desktop, com 8px onde eram 28.
  if (item.filhos.length === 0) {
    item.x = limites[item.nivel] || 0;
    registrar(item, limites);
    return;
  }
  for (var i = 0; i < item.filhos.length; i++) { posicionar(item.filhos[i], limites); }
  var primeiro = item.filhos[0], ultimo = item.filhos[item.filhos.length - 1];
  var centro = (primeiro.x + primeiro.w / 2 + ultimo.x + ultimo.w / 2) / 2;
  // Math.trunc e NAO Math.round: o Python usa int(), que trunca. Com arredondamento as duas
  // implementacoes saiam 1-2px diferentes -- pouco na tela, mas e assim que a duplicacao
  // comeca a divergir. O teste app/test/web_organograma.py compara as duas e acusa.
  item.x = Math.trunc(centro - item.w / 2);
  var minimo = limites[item.nivel] || 0;
  if (item.x < minimo) { deslocar(item, minimo - item.x); }
  registrar(item, limites);
}

function alturasPorNivel(item, alturas) {
  alturas[item.nivel] = Math.max(alturas[item.nivel] || 0, item.h);
  for (var i = 0; i < item.filhos.length; i++) { alturasPorNivel(item.filhos[i], alturas); }
}

function aplicarY(item, topo) {
  item.y = topo[item.nivel] || 0;
  for (var i = 0; i < item.filhos.length; i++) { aplicarY(item.filhos[i], topo); }
}

function layout(item) {
  medir(item);
  posicionar(item, {});
  var alturas = {};
  alturasPorNivel(item, alturas);
  var niveis = Object.keys(alturas).map(Number).sort(function(a, b){ return a - b; });
  var topo = {}, corrente = 0;
  for (var i = 0; i < niveis.length; i++) {
    topo[niveis[i]] = corrente;
    corrente += alturas[niveis[i]] + ESPACO_NIVEL;
  }
  aplicarY(item, topo);
}

// ---------------------------------------------------------------- desenho
function conectores(item) {
  if (item.filhos.length === 0) { return; }
  // Cotovelo, nao linha de centro a centro: e o que faz ler como hierarquia.
  ctx.strokeStyle = COR_CONECTOR; ctx.lineWidth = 1.4;
  var meioPai = item.x + item.w / 2, base = item.y + item.h, barra = base + ESPACO_NIVEL / 2;
  ctx.beginPath(); ctx.moveTo(meioPai, base); ctx.lineTo(meioPai, barra); ctx.stroke();
  var meios = item.filhos.map(function(f){ return f.x + f.w / 2; });
  if (meios.length > 1) {
    ctx.beginPath();
    ctx.moveTo(Math.min.apply(null, meios), barra);
    ctx.lineTo(Math.max.apply(null, meios), barra);
    ctx.stroke();
  }
  for (var i = 0; i < item.filhos.length; i++) {
    var meio = item.filhos[i].x + item.filhos[i].w / 2;
    ctx.beginPath(); ctx.moveTo(meio, barra); ctx.lineTo(meio, item.filhos[i].y); ctx.stroke();
  }
}

function caixaArredondada(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y,     x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x,     y + h, r);
  ctx.arcTo(x,     y + h, x,     y,     r);
  ctx.arcTo(x,     y,     x + w, y,     r);
  ctx.closePath();
}

function caixa(item) {
  var ehRaiz = item.nivel === 0;
  ctx.fillStyle = ehRaiz ? COR_FUNDO_RAIZ : COR_FUNDO;
  ctx.strokeStyle = COR_BORDA; ctx.lineWidth = ehRaiz ? 2 : 1;
  caixaArredondada(item.x, item.y, item.w, item.h, 5);
  ctx.fill(); ctx.stroke();

  ctx.fillStyle = COR_BORDA; ctx.font = FONTE_NEGRITO;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  var y = item.y + MARGEM_CAIXA;
  for (var i = 0; i < item.linhas_titulo.length; i++) {
    ctx.fillText(item.linhas_titulo[i], item.x + item.w / 2, y + ALTURA_TITULO / 2);
    y += ALTURA_TITULO;
  }
  if (item.linhas_nomes.length === 0) { return; }
  ctx.strokeStyle = COR_SEPARADOR; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(item.x + 6, y + 2); ctx.lineTo(item.x + item.w - 6, y + 2); ctx.stroke();
  y += 6;
  ctx.fillStyle = COR_SECUNDARIO; ctx.font = FONTE;
  for (var k = 0; k < item.linhas_nomes.length; k++) {
    ctx.fillText(item.linhas_nomes[k], item.x + item.w / 2, y + ALTURA_LINHA / 2);
    y += ALTURA_LINHA;
  }
}

function desenhar(item) {
  conectores(item);
  caixa(item);
  for (var i = 0; i < item.filhos.length; i++) { desenhar(item.filhos[i]); }
}

function todos(item, saida) {
  saida = saida || [];
  saida.push(item);
  for (var i = 0; i < item.filhos.length; i++) { todos(item.filhos[i], saida); }
  return saida;
}

function pintar() {
  if (raiz === null) { return; }
  var itens = todos(raiz);
  var maxX = 0, maxY = 0;
  for (var i = 0; i < itens.length; i++) {
    maxX = Math.max(maxX, itens[i].x + itens[i].w);
    maxY = Math.max(maxY, itens[i].y + itens[i].h);
  }
  var margem = 40;
  cv.width  = Math.round((maxX + margem * 2) * escala);
  cv.height = Math.round((maxY + margem * 2) * escala);
  ctx.setTransform(escala, 0, 0, escala, margem * escala, margem * escala);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(-margem, -margem, cv.width / escala + margem, cv.height / escala + margem);
  desenhar(raiz);
}

function zoomar(valor) { escala = Math.max(0.15, Math.min(4, valor)); pintar(); }
function zoom(fator)   { zoomar(escala * fator); }
function ajustar() {
  if (raiz === null) { return; }
  var itens = todos(raiz), maxX = 0, maxY = 0;
  for (var i = 0; i < itens.length; i++) {
    maxX = Math.max(maxX, itens[i].x + itens[i].w);
    maxY = Math.max(maxY, itens[i].y + itens[i].h);
  }
  var disponivel = document.querySelector(".tela").clientWidth - 20;
  zoomar(Math.min(1, disponivel / (maxX + 80)));
}

// ---------------------------------------------------------------- carga
function montarArvore(itens) {
  // O banco guarda a lista plana com o pai; a arvore e montada aqui, como no __addItem__ do
  // desktop. Item cujo pai nao existe (apagado a mao no banco) vira RAIZ, em vez de sumir.
  var porId = {}, raizes = [];
  itens.forEach(function(i){
    porId[i.id] = { id:i.id, texto:i.texto, entidades:i.entidades || [], filhos:[], nivel:0, x:0, y:0, w:0, h:0 };
  });
  itens.forEach(function(i){
    var pai = i.pai && porId[i.pai] ? porId[i.pai] : null;
    if (pai) { pai.filhos.push(porId[i.id]); } else { raizes.push(porId[i.id]); }
  });
  function nivelar(n, nivel) {
    n.nivel = nivel;
    n.filhos.forEach(function(f){ nivelar(f, nivel + 1); });
  }
  if (raizes.length === 0) { return null; }
  // Mais de uma raiz nao deveria existir (o modelo so aceita uma), mas se o banco tiver,
  // mostrar a primeira e esconder o resto seria mentira: pendura as outras numa raiz virtual.
  var topo = raizes.length === 1 ? raizes[0]
           : { id:null, texto:"(vários topos)", entidades:[], filhos:raizes, nivel:0, x:0, y:0, w:0, h:0 };
  nivelar(topo, 0);
  return topo;
}

var params = new URLSearchParams(window.location.search);
fetch("../../service/organizationchart_load.php?id=" + encodeURIComponent(params.get("id"))
      + "&domain=" + encodeURIComponent(params.get("domain")))
  .then(function(r){ return r.json(); })
  .then(function(js){
    if (js.error) { document.getElementById("aviso").textContent = js.error; return; }
    document.getElementById("titulo").textContent = js.name || "Organograma";
    document.getElementById("sub").textContent = js.organizacao ? ("organização: " + js.organizacao) : "";
    raiz = montarArvore(js.itens || []);
    if (raiz === null) {
      document.querySelector(".tela").innerHTML = '<p class="vazio">Este organograma ainda não tem itens.</p>';
      return;
    }
    layout(raiz);
    ajustar();
  })
  .catch(function(e){ document.getElementById("aviso").textContent = "Falha ao carregar: " + e; });
</script>
</body>
</html>
