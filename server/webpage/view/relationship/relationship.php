<?php
// Os parametros entram no JS via json_encode, que ja produz um literal de string
// escapado. Interpolar $_GET direto entre aspas deixava a pagina aberta a XSS.
$JS = JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT;
$map_id = isset($_GET["id"])     ? $_GET["id"]     : "";
$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";
?>
<!DOCTYPE html>
<html lang="pt-BR">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CML — Mapa de vínculos</title>
  <script src="../../public/jquery.min.js"></script>
  <link rel="stylesheet" href="../../public/cml.css">
<style>
/* Tokens, paleta e base: ../../public/cml.css (compartilhado com o index).
   Aqui fica so o que e especifico do mapa e das referencias. */

/* abas */
.tab { display: flex; gap: 2px; border-bottom: 1px solid var(--border); }
.tab button {
  background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--text-secondary); font: inherit; font-size: 14px;
  cursor: pointer; padding: 10px 14px; margin-bottom: -1px;
  transition: color .15s, border-color .15s;
}
.tab button:hover { color: var(--text-primary); }
.tab button.active { color: var(--text-primary); font-weight: 600; border-bottom-color: var(--person); }
.tab .cont { color: var(--muted); font-weight: 400; margin-left: 4px; }
.tabcontent { display: none; padding-top: 16px; }

/* barra de ferramentas do mapa: filtros/controles numa linha so, acima do grafico */
.toolbar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; flex-wrap: wrap; margin-bottom: 10px;
}
.zoom { display: flex; align-items: center; gap: 4px; }
.zoom button {
  background: var(--surface-1); border: 1px solid var(--border); border-radius: 6px;
  color: var(--text-secondary); font: inherit; cursor: pointer;
  min-width: 32px; height: 32px; padding: 0 9px;
  transition: background .15s, color .15s;
}
.zoom button:hover { background: var(--hover); color: var(--text-primary); }
.zoom .nivel {
  color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums;
  min-width: 46px; text-align: center;
}

/* legenda: identidade nunca fica so na cor — dot + rotulo, sempre presente */
.legenda { display: flex; gap: 16px; flex-wrap: wrap; }
.legenda span { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.legenda i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.legenda .li-person       { background: var(--person); }
.legenda .li-organization { background: var(--organization); }
.legenda .li-other        { background: var(--other); }
.legenda .li-link { width: 14px; height: 0; border-radius: 0; border-top: 2px solid var(--muted); }

#palco {
  position: relative; background: var(--surface-1);
  border: 1px solid var(--border); border-radius: 8px; overflow: hidden;
}
#mapa { display: block; cursor: grab; touch-action: none; }
#mapa.arrastando { cursor: grabbing; }

#dica {
  position: absolute; pointer-events: none; display: none; z-index: 5;
  max-width: 320px; background: var(--surface-1);
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px;
  box-shadow: 0 4px 14px rgba(0,0,0,.13);
}
#dica .t { font-weight: 600; margin-bottom: 2px; }
#dica .m { font-size: 12px; color: var(--muted); }
#dica .d { font-size: 12px; color: var(--text-secondary); margin-top: 5px; }

/* referencias */
.busca { margin-bottom: 4px; }
.busca input { width: 100%; max-width: 380px; }
.resumo { color: var(--muted); font-size: 12px; margin: 8px 0 4px 0; }

.entidade { padding: 14px 0; border-bottom: 1px solid var(--gridline); }
.entidade:last-child { border-bottom: none; }
.entidade h2 { font-size: 14px; font-weight: 600; margin: 0 0 8px 0; display: flex; align-items: center; gap: 8px; }
.entidade h2 i { width: 8px; height: 8px; border-radius: 2px; flex: none; }
.badge {
  font-size: 11px; font-weight: 400; color: var(--text-secondary);
  border: 1px solid var(--border); border-radius: 3px; padding: 0 6px;
}
.entidade ul { margin: 0; padding-left: 16px; }
.entidade li { margin-bottom: 9px; }
.entidade a { color: var(--person); text-decoration: none; }
.entidade a:hover { text-decoration: underline; }
.entidade .desc { color: var(--text-secondary); font-size: 13px; margin-top: 2px; }
.entidade .extra { font-size: 12px; margin-left: 6px; }
.sem-link { color: var(--text-primary); }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <a class="voltar" href="index.php?domain=<?php echo urlencode($domain); ?>"><span class="seta">←</span>Mapas de vínculos</a>
    <h1 id="map_name">Carregando…</h1>
    <div class="chips" id="map_keyword"></div>
  </header>
  <div id="tbl_abas" class="tab"></div>
  <div id="div_abas"></div>
</div>

<script>
var FONTE_NO = '13px system-ui, -apple-system, "Segoe UI", sans-serif';
var PAD_X = 10;          // respiro do rotulo dentro da caixa
var RAIO  = 5;
var MAPA  = null;
var PALETA = {};
var vista = { escala: 1, dx: 0, dy: 0 };

function lerPaleta(){
    // O canvas nao enxerga CSS custom properties: resolve aqui e redesenha quando o
    // tema muda, senao o grafico fica com as cores do modo anterior.
    var cs = getComputedStyle(document.documentElement);
    var pega = function(n){ return cs.getPropertyValue(n).trim(); };
    PALETA = {
        surface: pega("--surface-1"), texto: pega("--text-primary"),
        secundario: pega("--text-secondary"), muted: pega("--muted"),
        borda: pega("--gridline"),
        person: pega("--person"), organization: pega("--organization"), other: pega("--other")
    };
}

function corDe(etype){ return PALETA[etype] || PALETA.muted; }

// Fill saturado em bloco grande le pesado e derruba o contraste do rotulo. A cor entra
// como tinta do traco + um leve wash; o texto fica na tinta primaria.
function comAlfa(hex, a){
    var h = String(hex).replace("#","");
    if(h.length === 3){ h = h[0]+h[0]+h[1]+h[1]+h[2]+h[2]; }
    var n = parseInt(h, 16);
    return "rgba(" + ((n>>16)&255) + "," + ((n>>8)&255) + "," + (n&255) + "," + a + ")";
}

function caixaRedonda(ctx, x, y, w, h, r){
    r = Math.min(r, h/2, w/2);
    ctx.beginPath();
    ctx.moveTo(x+r, y);
    ctx.arcTo(x+w, y,   x+w, y+h, r);
    ctx.arcTo(x+w, y+h, x,   y+h, r);
    ctx.arcTo(x,   y+h, x,   y,   r);
    ctx.arcTo(x,   y,   x+w, y,   r);
    ctx.closePath();
}

// O PHP estima a largura por contagem de caracteres; so o navegador sabe a metrica real
// da fonte. Medir aqui e recalcular o centro elimina a divergencia entre a largura que o
// servidor reserva e a que o desenho ocupa.
function medir(mapa){
    var ctx = document.getElementById("mapa").getContext("2d");
    ctx.font = FONTE_NO;
    var porId = {};
    mapa.elements.forEach(function(e){
        var t = e.text_label || "";
        e._w  = Math.ceil(ctx.measureText(t).width) + PAD_X * 2;
        e._h  = Math.max(Number(e.h) || 20, 22);
        e._cx = Number(e.x) + e._w / 2;
        e._cy = Number(e.y) + e._h / 2;
        porId[e.id] = e;
    });
    // to/from chegam so com o centro do PHP; realinha com o centro medido. O tamanho vai
    // junto: sem ele o calculo da borda recebe caixa zero e a seta morre no centro do no,
    // escondida embaixo dele.
    mapa.elements.forEach(function(e){
        ["to","from"].forEach(function(k){
            (e[k] || []).forEach(function(p){
                var alvo = porId[p.id];
                if(alvo){ p._cx = alvo._cx; p._cy = alvo._cy; p._w = alvo._w; p._h = alvo._h; }
            });
        });
    });
    var maxX = 0, maxY = 0;
    mapa.elements.forEach(function(e){
        maxX = Math.max(maxX, Number(e.x) + e._w);
        maxY = Math.max(maxY, Number(e.y) + e._h);
    });
    mapa._w = maxX + 20;
    mapa._h = maxY + 20;
}

function seta(ctx, x1, y1, x2, y2){
    var a = Math.atan2(y2 - y1, x2 - x1);
    var L = 7;
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - L * Math.cos(a - Math.PI/7), y2 - L * Math.sin(a - Math.PI/7));
    ctx.lineTo(x2 - L * Math.cos(a + Math.PI/7), y2 - L * Math.sin(a + Math.PI/7));
    ctx.closePath();
    ctx.fill();
}

// Encosta a linha na borda da caixa em vez do centro: sem isto a seta fica escondida
// embaixo do no.
function naBorda(alvo, ox, oy){
    var cx = alvo._cx, cy = alvo._cy, hw = alvo._w/2 + 3, hh = alvo._h/2 + 3;
    var dx = ox - cx, dy = oy - cy;
    if(dx === 0 && dy === 0){ return [cx, cy]; }
    var t = Math.min( Math.abs(dx) > 0.001 ? hw/Math.abs(dx) : Infinity,
                      Math.abs(dy) > 0.001 ? hh/Math.abs(dy) : Infinity );
    return [cx + dx * t, cy + dy * t];
}

function desenharNo(ctx, e, destaque){
    var cor = corDe(e.etype);
    var x = Number(e.x), y = Number(e.y), w = e._w, h = e._h;

    if(e.etype === "link"){
        // Vinculo nao e categoria: e a estrutura que liga as entidades. Fica neutro para
        // nao competir com os slots categoricos nem gastar um deles.
        ctx.save();
        ctx.setLineDash([4, 3]);
        caixaRedonda(ctx, x, y, w, h, RAIO);
        ctx.fillStyle = PALETA.surface; ctx.fill();
        ctx.strokeStyle = PALETA.muted; ctx.lineWidth = 1; ctx.stroke();
        ctx.restore();
        ctx.fillStyle = PALETA.secundario;
    } else {
        caixaRedonda(ctx, x, y, w, h, e.etype === "person" ? h/2 : RAIO);
        ctx.fillStyle = comAlfa(cor, destaque ? 0.26 : 0.14); ctx.fill();
        ctx.strokeStyle = cor; ctx.lineWidth = destaque ? 2 : 1.5; ctx.stroke();
        ctx.fillStyle = PALETA.texto;
    }
    // Rotulo direto em todo no: e a relief que o validador exige para os slots de baixo
    // contraste, e o que faz a identidade nao depender so da cor.
    ctx.font = FONTE_NO;
    ctx.textBaseline = "middle";
    ctx.fillText(e.text_label || "", x + PAD_X, y + h/2 + 0.5);
}

function desenhar(){
    var canvas = document.getElementById("mapa");
    var ctx = canvas.getContext("2d");
    var dpr = window.devicePixelRatio || 1;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = PALETA.surface;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(dpr * vista.escala, 0, 0, dpr * vista.escala, dpr * vista.dx, dpr * vista.dy);

    // vinculos primeiro: as linhas ficam atras das caixas
    ctx.strokeStyle = PALETA.muted;
    ctx.fillStyle   = PALETA.muted;
    ctx.lineWidth   = 1.5;
    MAPA.elements.forEach(function(e){
        if(e.etype !== "link"){ return; }
        // Direcao por seta, nao por cor: origem -> vinculo -> destino.
        (e.from || []).forEach(function(p){
            if(p._cx == null){ return; }
            var origem  = naBorda(p, e._cx, e._cy);   // sai da borda da entidade
            var chegada = naBorda(e, p._cx, p._cy);   // chega na borda do vinculo
            ctx.beginPath(); ctx.moveTo(origem[0], origem[1]); ctx.lineTo(chegada[0], chegada[1]); ctx.stroke();
            seta(ctx, origem[0], origem[1], chegada[0], chegada[1]);
        });
        (e.to || []).forEach(function(p){
            if(p._cx == null){ return; }
            var origem  = naBorda(e, p._cx, p._cy);   // sai da borda do vinculo
            var chegada = naBorda(p, e._cx, e._cy);   // chega na borda da entidade
            ctx.beginPath(); ctx.moveTo(origem[0], origem[1]); ctx.lineTo(chegada[0], chegada[1]); ctx.stroke();
            seta(ctx, origem[0], origem[1], chegada[0], chegada[1]);
        });
    });
    MAPA.elements.forEach(function(e){ if(e.etype === "link"){ desenharNo(ctx, e, false); } });
    MAPA.elements.forEach(function(e){ if(e.etype !== "link"){ desenharNo(ctx, e, e._hover); } });
}

function dimensionar(){
    var canvas = document.getElementById("mapa");
    var palco  = document.getElementById("palco");
    var dpr = window.devicePixelRatio || 1;
    var largura = palco.clientWidth;
    var altura  = Math.max(360, Math.min(640, MAPA._h + 40));
    canvas.width  = Math.round(largura * dpr);
    canvas.height = Math.round(altura * dpr);
    canvas.style.width  = largura + "px";
    canvas.style.height = altura + "px";
}

function ajustar(){
    var canvas = document.getElementById("mapa");
    var dpr = window.devicePixelRatio || 1;
    var lv = canvas.width / dpr, av = canvas.height / dpr;
    var e = Math.min(lv / MAPA._w, av / MAPA._h, 1);
    vista.escala = e;
    vista.dx = (lv - MAPA._w * e) / 2;
    vista.dy = (av - MAPA._h * e) / 2;
    nivel(); desenhar();
}

function nivel(){ $("#nivel").text(Math.round(vista.escala * 100) + "%"); }

function zoom(fator, ancoraX, ancoraY){
    var canvas = document.getElementById("mapa");
    var dpr = window.devicePixelRatio || 1;
    if(ancoraX == null){ ancoraX = canvas.width / dpr / 2; ancoraY = canvas.height / dpr / 2; }
    var nova = Math.max(0.15, Math.min(4, vista.escala * fator));
    // ancora o zoom no ponto apontado, senao o conteudo foge do cursor
    vista.dx = ancoraX - (ancoraX - vista.dx) * (nova / vista.escala);
    vista.dy = ancoraY - (ancoraY - vista.dy) * (nova / vista.escala);
    vista.escala = nova;
    nivel(); desenhar();
}

function noEm(mx, my){
    var x = (mx - vista.dx) / vista.escala;
    var y = (my - vista.dy) / vista.escala;
    for(var i = MAPA.elements.length - 1; i >= 0; i--){
        var e = MAPA.elements[i];
        // area de toque com folga: caixa de 22px e alvo pequeno demais no ponteiro
        if(x >= e.x - 3 && x <= Number(e.x) + e._w + 3 && y >= e.y - 3 && y <= Number(e.y) + e._h + 3){
            return e;
        }
    }
    return null;
}

var ROTULO = { person: "Pessoa", organization: "Organização", other: "Outro", link: "Vínculo" };

function dica(e, mx, my){
    var d = $("#dica");
    if(!e){ d.hide(); return; }
    d.empty();
    d.append($("<div class='t'>").text(e.text_label || "(sem nome)"));
    var meta = ROTULO[e.etype] || e.etype;
    var n = (e.references || []).length;
    if(n > 0){ meta += " · " + n + (n == 1 ? " referência" : " referências"); }
    d.append($("<div class='m'>").text(meta));
    if(e.full_description){
        var t = String(e.full_description).trim();
        d.append($("<div class='d'>").text(t.length > 260 ? t.slice(0, 260) + "…" : t));
    }
    var palco = document.getElementById("palco");
    var lim = palco.clientWidth;
    d.show();
    var lg = d.outerWidth();
    d.css({ left: Math.max(4, Math.min(mx + 14, lim - lg - 4)) + "px", top: (my + 14) + "px" });
}

// So http/https vira link clicavel: as referencias sao texto digitado pelo usuario, e um
// "javascript:..." colado ali executaria ao clique.
function urlSegura(u){
    if(!u){ return null; }
    var s = String(u).trim();
    return /^https?:\/\//i.test(s) ? s : null;
}

function linkRef(url, texto){
    return $("<a>").attr("href", url).attr("target", "_blank")
                   .attr("rel", "noopener noreferrer").text(texto);
}

function agruparPorEntidade(mapa){
    // As referencias sao da entidade, nao da caixa: se duas caixas do mapa apontarem para
    // a mesma entidade, a lista apareceria duas vezes.
    var vistos = {}, grupos = [];
    for(var i = 0; i < mapa.elements.length; i++){
        var el = mapa.elements[i];
        if(!el.references || el.references.length == 0){ continue; }
        if(vistos[el.entity_id]){ continue; }
        vistos[el.entity_id] = true;
        grupos.push(el);
    }
    grupos.sort(function(a, b){
        return String(a.text_label || "").localeCompare(String(b.text_label || ""), "pt-BR");
    });
    return grupos;
}

function casa(el, termo){
    if(!termo){ return true; }
    var alvo = (el.text_label || "") + " " + (el.references || []).map(function(r){
        return (r.title || "") + " " + (r.descricao || "") + " " + (r.link1 || "");
    }).join(" ");
    return alvo.toLowerCase().indexOf(termo) >= 0;
}

function montarReferencias(mapa, destino, termo){
    destino.empty();
    var grupos = agruparPorEntidade(mapa).filter(function(g){ return casa(g, termo); });

    if(grupos.length == 0){
        destino.append($("<p class='aviso'>").text(
            termo ? "Nenhuma referência encontrada para “" + termo + "”." : "Este mapa não tem referências."
        ));
        return;
    }
    var total = 0;
    grupos.forEach(function(g){ total += g.references.length; });
    destino.append($("<p class='resumo'>").text(
        total + (total == 1 ? " referência em " : " referências em ") +
        grupos.length + (grupos.length == 1 ? " entidade" : " entidades")
    ));

    grupos.forEach(function(el){
        var bloco = $("<div class='entidade'>");
        var h2 = $("<h2>");
        // dot + badge: a mesma identidade do mapa, e nunca so a cor
        h2.append($("<i>").css("background", corDe(el.etype)));
        h2.append(document.createTextNode(el.text_label || "(sem nome)"));
        h2.append($("<span class='badge'>").text(ROTULO[el.etype] || el.etype));
        bloco.append(h2);

        var ul = $("<ul>");
        el.references.forEach(function(ref){
            var li = $("<li>");
            var rotulo = ref.title || "(sem título)";
            var principal = urlSegura(ref.link1);
            if(principal){ li.append(linkRef(principal, rotulo)); }
            else { li.append($("<span class='sem-link'>").text(rotulo)); }

            var n = 2;
            [ref.link2, ref.link3].forEach(function(x){
                var u = urlSegura(x);
                if(u){ li.append($("<span class='extra'>").append(linkRef(u, "[" + n + "]"))); n++; }
            });
            if(ref.descricao && String(ref.descricao).trim() != ""){
                li.append($("<div class='desc'>").text(ref.descricao));
            }
            ul.append(li);
        });
        bloco.append(ul);
        destino.append(bloco);
    });
}

function aba(rotulo, contagem, id_conteudo, ativa){
    var btn = $("<button class='tablinks'>").text(rotulo);
    if(contagem != null){ btn.append($("<span class='cont'>").text(contagem)); }
    if(ativa){ btn.addClass("active"); }
    btn.on("click", function(evt){ abrirAba(evt, id_conteudo); });
    $("#tbl_abas").append(btn);
    var div = $("<div class='tabcontent'>").attr("id", id_conteudo);
    if(ativa){ div.css("display", "block"); }
    $("#div_abas").append(div);
    return div;
}

function abrirAba(evt, id_conteudo){
    $("#div_abas").children().css("display", "none");
    $("#tbl_abas").children().removeClass("active");
    $("#" + id_conteudo).css("display", "block");
    $(evt.currentTarget).addClass("active");
    if(id_conteudo === "div_mapa"){ dimensionar(); ajustar(); }
}

function montarMapa(destino){
    var barra = $("<div class='toolbar'>");
    var z = $("<div class='zoom'>");
    z.append($("<button title='Diminuir'>").text("−").on("click", function(){ zoom(1/1.25); }));
    z.append($("<span class='nivel' id='nivel'>"));
    z.append($("<button title='Aumentar'>").text("+").on("click", function(){ zoom(1.25); }));
    z.append($("<button title='Ajustar à tela'>").text("Ajustar").on("click", ajustar));
    barra.append(z);

    var leg = $("<div class='legenda'>");
    [["person","Pessoa"],["organization","Organização"],["other","Outro"],["link","Vínculo"]].forEach(function(p){
        leg.append($("<span>").append($("<i class='li-" + p[0] + "'>")).append(document.createTextNode(p[1])));
    });
    barra.append(leg);
    destino.append(barra);

    destino.append($("<div id='palco'>").append($("<canvas id='mapa'>")).append($("<div id='dica'>")));
}

function ligarInteracao(){
    var canvas = document.getElementById("mapa");
    var arrastando = false, ax = 0, ay = 0, moveu = false;

    $(canvas).on("mousedown", function(ev){
        arrastando = true; moveu = false;
        ax = ev.offsetX; ay = ev.offsetY;
        $(canvas).addClass("arrastando");
    });
    $(document).on("mouseup", function(){ arrastando = false; $(canvas).removeClass("arrastando"); });
    $(canvas).on("mousemove", function(ev){
        if(arrastando){
            moveu = true;
            vista.dx += ev.offsetX - ax; vista.dy += ev.offsetY - ay;
            ax = ev.offsetX; ay = ev.offsetY;
            $("#dica").hide();
            desenhar();
            return;
        }
        var e = noEm(ev.offsetX, ev.offsetY);
        var mudou = false;
        MAPA.elements.forEach(function(x){
            var novo = (x === e);
            if(!!x._hover !== novo){ x._hover = novo; mudou = true; }
        });
        if(mudou){ desenhar(); }
        // A dica enriquece, nunca e o unico caminho: o rotulo esta no no e a aba de
        // referencias lista tudo em texto.
        dica(e, ev.offsetX, ev.offsetY);
    });
    $(canvas).on("mouseleave", function(){ $("#dica").hide(); });
    canvas.addEventListener("wheel", function(ev){
        ev.preventDefault();
        zoom(ev.deltaY < 0 ? 1.12 : 1/1.12, ev.offsetX, ev.offsetY);
    }, { passive: false });

    $(window).on("resize", function(){ if($("#div_mapa").is(":visible")){ dimensionar(); desenhar(); } });

    // O tema pode mudar com a pagina aberta; o canvas nao reage a CSS sozinho.
    if(window.matchMedia){
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function(){
            lerPaleta(); desenhar();
        });
    }
}

function callbackMap(js){
    MAPA = js;
    document.title = (js.name || "Mapa") + " — CML";
    $("#map_name").text(js.name || "(mapa sem nome)");
    if(js.keyword){
        String(js.keyword).split(",").forEach(function(k){
            k = k.trim();
            if(k){ $("#map_keyword").append($("<span class='chip'>").text(k)); }
        });
    }

    var nRefs = agruparPorEntidade(js).reduce(function(s, g){ return s + g.references.length; }, 0);
    var aba_mapa = aba("Mapa", js.elements.length, "div_mapa", true);
    var aba_refs = aba("Referências", nRefs, "div_referencias", false);

    montarMapa(aba_mapa);
    lerPaleta();
    // medir() antes de dimensionar(): a altura do palco vem de MAPA._h, que so existe
    // depois da medicao. Invertido, o canvas nascia com altura NaN e nada era desenhado.
    medir(js);
    dimensionar();
    ajustar();
    ligarInteracao();

    var busca = $("<div class='busca'>").append(
        $("<input type='search' placeholder='Filtrar por entidade, título ou descrição…'>")
          .on("input", function(){ montarReferencias(js, $("#lista_refs"), this.value.trim().toLowerCase()); })
    );
    aba_refs.append(busca).append($("<div id='lista_refs'>"));
    montarReferencias(js, $("#lista_refs"), "");
}

function getMap(id, domain, callback){
   $.ajax({
      url : "../../service/relationship_load.php",
      data : { id : id, domain : domain },
      success : function(result){
        callback((typeof result === "string") ? JSON.parse(result) : result);
      },
      error : function(xhr){
        $("#map_name").text("Não foi possível carregar o mapa.");
        // o service devolve {"error": "..."} nas falhas tratadas; so cai no HTTP cru
        // quando a resposta nem JSON e (500, timeout, proxy no meio).
        var motivo = "HTTP " + xhr.status;
        try {
          var js = JSON.parse(xhr.responseText);
          if(js && js.error){ motivo = js.error; }
        } catch(e) { }
        $("#map_keyword").append($("<span class='chip'>").text(motivo));
      }
   });
}

getMap(<?php echo json_encode($map_id, $JS); ?>, <?php echo json_encode($domain, $JS); ?>, callbackMap);
</script>

</body>
</html>
