<?php
// Linha do tempo no site publico (somente leitura).
//
// ⚠️ SEGUNDA IMPLEMENTACAO do desenho que esta em app/classlib/timeline/timeline.py. No
// desktop a timeline nao guarda geometria -- a posicao de um evento E a data dele -- entao nao
// ha o que reusar aqui. Decisao do dono (2026-10-06), caminho A do SPEC.md §11: mudou o
// desenho la, muda aqui. As constantes e os nomes foram mantidos iguais de proposito.

$id     = isset($_GET["id"])     ? $_GET["id"]     : "";
$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CML — linha do tempo</title>
  <link rel="stylesheet" href="../../public/cml.css">
<style>
.topo { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; }
.barra { display:flex; gap:6px; align-items:center; margin:10px 0; flex-wrap:wrap; }
.barra button { padding:6px 12px; }
.tela { border:1px solid var(--border); border-radius:8px; overflow:auto; background:#fff;
        max-height:calc(100vh - 230px); }
#canvas { display:block; }
.legenda { display:flex; gap:14px; flex-wrap:wrap; margin:10px 0 0; font-size:12px; color:var(--muted); }
.legenda span.cor { display:inline-block; width:11px; height:11px; border-radius:2px; margin-right:5px; vertical-align:-1px; }
.vazio { padding:30px; color:var(--muted); }
</style>
</head>
<body>
<div class="wrap">
  <header class="topo">
    <h1 id="titulo">Linha do tempo</h1>
    <span class="tag" id="sub"></span>
  </header>
  <p><a href="../relationship/index.php?domain=<?php echo urlencode($domain); ?>">← voltar à lista</a></p>
  <div class="barra">
    <button onclick="zoom(1.3)">Zoom +</button>
    <button onclick="zoom(1/1.3)">Zoom −</button>
    <button onclick="zoomar(1)">100%</button>
    <span class="tag" id="aviso"></span>
  </div>
  <div class="tela"><canvas id="canvas" width="100" height="100"></canvas></div>
  <div class="legenda" id="legenda"></div>
</div>

<script>
// ---------------------------------------------------------------- constantes (= timeline.py)
var MARGEM_ESQ     = 80;
var MARGEM_DIR     = 40;
var TOPO           = 20;
var ALT_BARRA      = 13;
var NIVEL_BARRA    = 31;
var NIVEL_MARCO    = 33;
var FOLGA_VERTICAL = 22;
var FOLGA_NIVEL    = 14;
var BASE_LARGURA   = 1100;
var ALT_MINIMA     = 260;

// Mesmas cores e rotulos do timeline_event.py: a legenda sai daqui para nao discordar do
// desenho -- que e a mesma razao de eles morarem juntos no desktop.
var ORIGENS = {
  evento:        { cor:"#d68c14", rotulo:"Evento marcado" },
  referencia:    { cor:"#2a8494", rotulo:"Acontecimento (referência)" },
  vinculo:       { cor:"#c43c3c", rotulo:"Vínculo" },
  classificacao: { cor:"#5c5cb0", rotulo:"Classificação" },
  entidade:      { cor:"#348a5c", rotulo:"Entidade" },
  elemento:      { cor:"#687a8e", rotulo:"Caixa no mapa" }
};

var FONTE = "12px 'DejaVu Sans', sans-serif";
var ALTURA_TEXTO = 15;   // equivalente ao metrica.height() do Qt para esta fonte

var cv = document.getElementById("canvas");
var ctx = cv.getContext("2d");
var EVENTOS = [], zoomAtual = 1;
var domIni = null, domFim = null, larguraEixo = 0, eixoY = 0, alturaTotal = 0, folgaDireita = MARGEM_DIR;
var ticks = [], niveisBarra = 0, niveisMarco = 0;
var passoBarra = NIVEL_BARRA, passoMarco = NIVEL_MARCO;

function dias(texto){ return Math.floor(Date.parse(texto + "T00:00:00Z") / 86400000); }
function pontual(e){ return e.fim === null || e.fim === e.inicio; }
function rotulo(e){ return e.detalhe ? (e.titulo + " · " + e.detalhe) : e.titulo; }

function xDaData(texto){
  if (domIni === domFim) { return MARGEM_ESQ + larguraEixo / 2; }
  var fracao = (dias(texto) - dias(domIni)) / (dias(domFim) - dias(domIni));
  return MARGEM_ESQ + fracao * larguraEixo;
}

function dominio(){
  var menor = null, maior = null;
  EVENTOS.forEach(function(e){
    if (menor === null || e.inicio < menor) { menor = e.inicio; }
    var fim = e.fim || e.inicio;
    if (maior === null || fim > maior) { maior = fim; }
  });
  // Uma folga de 4% nas pontas: evento no extremo exato encosta na borda e some.
  var span = Math.max(1, dias(maior) - dias(menor));
  var folga = Math.max(1, Math.round(span * 0.04));
  domIni = new Date((dias(menor) - folga) * 86400000).toISOString().slice(0, 10);
  domFim = new Date((dias(maior) + folga) * 86400000).toISOString().slice(0, 10);
}

function montarTicks(){
  var anoIni = parseInt(domIni.slice(0, 4), 10), anoFim = parseInt(domFim.slice(0, 4), 10);
  var span = anoFim - anoIni;
  // Passo que mantenha ~12 marcas: com um tick por ano num período de 40 anos o eixo vira
  // uma régua ilegível.
  var passo = span <= 12 ? 1 : (span <= 30 ? 2 : (span <= 60 ? 5 : (span <= 150 ? 10 : 25)));
  ticks = [];
  for (var ano = Math.ceil(anoIni / passo) * passo; ano <= anoFim; ano += passo) {
    ticks.push({ ano: ano, x: xDaData(ano + "-01-01") });
  }
}

function nivelLivre(ocupado, inicio, fim){
  for (var i = 0; i < ocupado.length; i++) {
    if (inicio >= ocupado[i]) { ocupado[i] = fim; return i; }
  }
  ocupado.push(fim);
  return ocupado.length - 1;
}

function recalc(){
  ctx.font = FONTE;
  passoBarra = Math.max(NIVEL_BARRA, ALTURA_TEXTO + 3 + ALT_BARRA + FOLGA_VERTICAL);
  passoMarco = Math.max(NIVEL_MARCO, ALTURA_TEXTO + 2 + FOLGA_VERTICAL);
  larguraEixo = Math.max(400, BASE_LARGURA * zoomAtual);
  if (EVENTOS.length === 0) {
    domIni = domFim = null; niveisBarra = niveisMarco = 0;
    folgaDireita = MARGEM_DIR; eixoY = TOPO + 60; alturaTotal = ALT_MINIMA; ticks = [];
    return;
  }
  dominio();
  montarTicks();

  // Dois empilhadores: barras acima do eixo, marcos abaixo. Cada nível guarda até onde já foi
  // escrito; o evento entra no primeiro livre. A lista vem ordenada por início, então uma
  // passada basta.
  var ocupadoBarra = [], ocupadoMarco = [];
  EVENTOS.forEach(function(e){
    var xIni = xDaData(e.inicio);
    var larguraTexto = ctx.measureText(rotulo(e)).width;
    if (pontual(e)) {
      // De que lado escrever. Sempre à direita joga o texto para fora quando os eventos se
      // concentram no fim do período -- o caso comum numa investigação.
      var espacoDireita = (MARGEM_ESQ + larguraEixo) - xIni;
      var espacoEsquerda = xIni - MARGEM_ESQ;
      var precisa = larguraTexto + 20;
      if (precisa <= espacoDireita && xIni <= MARGEM_ESQ + larguraEixo * 0.55) { e.esquerda = false; }
      else if (precisa <= espacoEsquerda) { e.esquerda = true; }
      else if (precisa <= espacoDireita)  { e.esquerda = false; }
      else { e.esquerda = espacoEsquerda > espacoDireita; }
      var ini = e.esquerda ? (xIni - larguraTexto - 14) : (xIni - 6);
      var fim = e.esquerda ? (xIni + 10 + FOLGA_NIVEL) : (xIni + larguraTexto + FOLGA_NIVEL + 12);
      e.nivel = nivelLivre(ocupadoMarco, ini, fim);
      e.x = ini; e.w = Math.max(20, fim - ini - FOLGA_NIVEL); e.h = Math.max(24, ALTURA_TEXTO + 4);
    } else {
      var xFim = xDaData(e.fim);
      var fimOcupado = Math.max(xFim, xIni + larguraTexto) + FOLGA_NIVEL;
      e.nivel = nivelLivre(ocupadoBarra, xIni, fimOcupado);
      e.x = xIni; e.w = Math.max(xFim - xIni, larguraTexto, 4);
      e.h = ALT_BARRA + ALTURA_TEXTO + 2;
    }
  });
  niveisBarra = ocupadoBarra.length;
  niveisMarco = ocupadoMarco.length;

  // Rótulo que passa da borda direita faz a margem crescer até caber.
  var extremo = 0;
  ocupadoBarra.concat(ocupadoMarco).forEach(function(f){ extremo = Math.max(extremo, f); });
  folgaDireita = Math.max(MARGEM_DIR, extremo - (MARGEM_ESQ + larguraEixo) + 20);

  eixoY = TOPO + 30 + niveisBarra * passoBarra;
  alturaTotal = Math.max(ALT_MINIMA, eixoY + 40 + niveisMarco * passoMarco);
}

function desenhar(){
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, cv.width / zoomPixel, cv.height / zoomPixel);
  if (EVENTOS.length === 0) { return; }
  ctx.font = FONTE; ctx.textBaseline = "middle";

  // eixo
  ctx.strokeStyle = "#8d9aa7"; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(MARGEM_ESQ, eixoY); ctx.lineTo(MARGEM_ESQ + larguraEixo, eixoY); ctx.stroke();
  ctx.strokeStyle = "#dde3ea"; ctx.lineWidth = 1;
  ctx.fillStyle = "#6b7684"; ctx.textAlign = "center";
  ticks.forEach(function(t){
    ctx.beginPath(); ctx.moveTo(t.x, TOPO); ctx.lineTo(t.x, alturaTotal - 10); ctx.stroke();
    ctx.fillText(String(t.ano), t.x, eixoY + 12);
  });

  EVENTOS.forEach(function(e){
    var cor = (ORIGENS[e.origem] || ORIGENS.elemento).cor;
    if (pontual(e)) {
      var x = xDaData(e.inicio);
      var y = eixoY + 26 + e.nivel * passoMarco;
      ctx.strokeStyle = cor; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(x, eixoY); ctx.lineTo(x, y); ctx.stroke();
      ctx.fillStyle = cor;
      ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill();
      ctx.textAlign = e.esquerda ? "right" : "left";
      ctx.fillStyle = "#2d3440";
      ctx.fillText(rotulo(e), e.esquerda ? x - 9 : x + 9, y);
    } else {
      var xi = xDaData(e.inicio), xf = xDaData(e.fim);
      var yb = eixoY - 24 - e.nivel * passoBarra;
      ctx.fillStyle = cor;
      ctx.globalAlpha = 0.85;
      ctx.fillRect(xi, yb, Math.max(3, xf - xi), ALT_BARRA);
      ctx.globalAlpha = 1;
      ctx.textAlign = "left"; ctx.fillStyle = "#2d3440";
      ctx.fillText(rotulo(e), xi, yb - 9);
    }
  });
}

var zoomPixel = 1;
function pintar(){
  recalc();
  cv.width  = Math.round(MARGEM_ESQ + larguraEixo + folgaDireita);
  cv.height = Math.round(alturaTotal);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  desenhar();
  montarLegenda();
}
function zoomar(v){ zoomAtual = Math.max(0.3, Math.min(8, v)); pintar(); }
function zoom(f){ zoomar(zoomAtual * f); }

function montarLegenda(){
  // Só as origens que aparecem: legenda com item que não está no desenho faz procurar o que
  // não existe.
  var presentes = {};
  EVENTOS.forEach(function(e){ presentes[e.origem] = true; });
  var destino = document.getElementById("legenda");
  destino.innerHTML = "";
  Object.keys(ORIGENS).forEach(function(chave){
    if (!presentes[chave]) { return; }
    var item = document.createElement("span");
    var cor = document.createElement("span");
    cor.className = "cor"; cor.style.background = ORIGENS[chave].cor;
    item.appendChild(cor);
    item.appendChild(document.createTextNode(ORIGENS[chave].rotulo));
    destino.appendChild(item);
  });
}

var params = new URLSearchParams(window.location.search);
fetch("../../service/timeline_load.php?id=" + encodeURIComponent(params.get("id"))
      + "&domain=" + encodeURIComponent(params.get("domain")))
  .then(function(r){ return r.json(); })
  .then(function(js){
    if (js.error) { document.getElementById("aviso").textContent = js.error; return; }
    document.getElementById("titulo").textContent = js.name || "Linha do tempo";
    // Timeline SOLTA é legítima: dizer isso evita parecer defeito.
    document.getElementById("sub").textContent =
      js.mapa_nome ? ("projeta o mapa: " + js.mapa_nome) : "sem mapa de origem";
    EVENTOS = js.eventos || [];
    if (EVENTOS.length === 0) {
      document.querySelector(".tela").innerHTML =
        '<p class="vazio">Nenhuma data para desenhar: nem evento marcado, nem data projetada do mapa.</p>';
      return;
    }
    pintar();
  })
  .catch(function(e){ document.getElementById("aviso").textContent = "Falha ao carregar: " + e; });
</script>
</body>
</html>
