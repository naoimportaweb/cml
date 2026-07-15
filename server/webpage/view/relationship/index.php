<?php
// Os parametros entram no JS via json_encode, que ja produz um literal de string escapado.
// Interpolar $_GET direto entre aspas deixaria a pagina aberta a XSS.
$JS = JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT;
$domain = isset($_GET["domain"]) ? $_GET["domain"] : "";
?>
<!DOCTYPE html>
<html lang="pt-BR">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CML — Mapas de vínculos</title>
  <script src="../../public/jquery.min.js"></script>
  <link rel="stylesheet" href="../../public/cml.css">
<style>
/* uma linha de filtro acima de tudo que ela escopa */
.filtros {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin-bottom: 12px;
}
.filtros input[type="search"] { flex: 1 1 280px; max-width: 420px; }
.filtros label { color: var(--muted); font-size: 12px; }
.filtros .resumo { color: var(--muted); font-size: 12px; margin-left: auto; }

.tabela {
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 8px; overflow-x: auto;
}
table { width: 100%; border-collapse: collapse; }
thead th {
  text-align: left; font-size: 12px; font-weight: 600; color: var(--text-secondary);
  border-bottom: 1px solid var(--border); padding: 10px 14px;
  cursor: pointer; user-select: none; white-space: nowrap;
}
thead th:hover { background: var(--hover); color: var(--text-primary); }
thead th .seta { color: var(--muted); font-size: 10px; margin-left: 4px; }
thead th.num, tbody td.num { text-align: right; font-variant-numeric: tabular-nums; }

tbody tr { border-bottom: 1px solid var(--gridline); }
tbody tr:last-child { border-bottom: none; }
tbody tr:hover { background: var(--hover); }
tbody td { padding: 11px 14px; vertical-align: top; }

td.nome a { color: var(--text-primary); text-decoration: none; font-weight: 600; }
td.nome a:hover { color: var(--person); text-decoration: underline; }
td.nome .kw { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; }
td.nome .kw span {
  font-size: 11px; color: var(--text-secondary);
  border: 1px solid var(--border); border-radius: 999px; padding: 0 7px;
}
td.autor, td.data { color: var(--text-secondary); font-size: 13px; white-space: nowrap; }
td.num { color: var(--text-secondary); }
td.num.zero { color: var(--muted); }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Mapas de vínculos</h1>
    <div class="chips" id="cab"></div>
  </header>

  <div class="filtros">
    <input type="search" id="busca" placeholder="Filtrar por nome, palavra-chave ou autor…">
    <label for="ordem">Ordenar</label>
    <select id="ordem">
      <option value="name">Nome</option>
      <option value="modification_time">Modificado recentemente</option>
      <option value="creation_time">Criado recentemente</option>
      <option value="elementos">Mais elementos</option>
      <option value="referencias">Mais referências</option>
      <option value="username">Autor</option>
    </select>
    <span class="resumo" id="resumo"></span>
  </div>

  <div class="tabela" id="tabela"></div>
</div>

<script>
var DOMAIN = <?php echo json_encode($domain, $JS); ?>;
var MAPAS = [];
var ordem = { campo: "name", desc: false };

// 'texto' decide a comparacao. As datas vem do MySQL como 'YYYY-MM-DD HH:MM:SS', que
// ordena certo comparado como string — nao precisa de Date.
var COLUNAS = [
  { campo: "name",              rotulo: "Nome",        texto: true,  classe: "nome"  },
  { campo: "username",          rotulo: "Autor",       texto: true,  classe: "autor" },
  { campo: "elementos",         rotulo: "Elementos",   texto: false, classe: "num"   },
  { campo: "referencias",       rotulo: "Referências", texto: false, classe: "num"   },
  { campo: "modification_time", rotulo: "Modificado",  texto: true,  classe: "data"  }
];

function textoBusca(m){
  return ((m.name || "") + " " + (m.keyword || "") + " " + (m.username || "")).toLowerCase();
}

function filtrar(termo){
  if(!termo){ return MAPAS.slice(); }
  return MAPAS.filter(function(m){ return textoBusca(m).indexOf(termo) >= 0; });
}

function padraoDesc(c){
  // contagens e datas comecam do maior; texto comeca de A-Z
  return c ? (!c.texto || c.campo.indexOf("_time") > 0) : false;
}

function ordenar(lista){
  var c = COLUNAS.filter(function(x){ return x.campo === ordem.campo; })[0];
  var texto = c ? c.texto : true;
  var s = lista.slice().sort(function(a, b){
    var x = a[ordem.campo], y = b[ordem.campo];
    var r;
    if(texto){
      r = String(x == null ? "" : x).localeCompare(String(y == null ? "" : y), "pt-BR");
    } else {
      r = (Number(x) || 0) - (Number(y) || 0);
    }
    // desempate estavel pelo nome: sem isto mapas com a mesma contagem trocam de lugar a
    // cada reordenacao
    if(r === 0){ return String(a.name || "").localeCompare(String(b.name || ""), "pt-BR"); }
    return r;
  });
  return ordem.desc ? s.reverse() : s;
}

function dataCurta(s){
  if(!s){ return "—"; }
  var p = String(s).split(" ")[0].split("-");
  return p.length === 3 ? (p[2] + "/" + p[1] + "/" + p[0]) : String(s);
}

function montarCabecalho(){
  var tr = $("<tr>");
  COLUNAS.forEach(function(c){
    var th = $("<th>").addClass(c.classe === "num" ? "num" : "").text(c.rotulo);
    if(ordem.campo === c.campo){
      th.append($("<span class='seta'>").text(ordem.desc ? "▼" : "▲"));
    }
    th.on("click", function(){
      if(ordem.campo === c.campo){ ordem.desc = !ordem.desc; }
      else { ordem.campo = c.campo; ordem.desc = padraoDesc(c); }
      $("#ordem").val(ordem.campo);
      render();
    });
    tr.append(th);
  });
  return $("<thead>").append(tr);
}

function linha(m){
  var tr = $("<tr>");

  var td = $("<td class='nome'>");
  var url = "relationship.php?id=" + encodeURIComponent(m.id) + "&domain=" + encodeURIComponent(DOMAIN);
  td.append($("<a>").attr("href", url).text(m.name || "(mapa sem nome)"));
  if(m.keyword){
    var kw = $("<div class='kw'>");
    String(m.keyword).split(",").forEach(function(k){
      k = k.trim();
      if(k){ kw.append($("<span>").text(k)); }
    });
    td.append(kw);
  }
  tr.append(td);

  tr.append($("<td class='autor'>").text(m.username || "—"));
  tr.append($("<td class='num'>").addClass(m.elementos   ? "" : "zero").text(m.elementos));
  tr.append($("<td class='num'>").addClass(m.referencias ? "" : "zero").text(m.referencias));
  tr.append($("<td class='data'>").text(dataCurta(m.modification_time || m.creation_time)));
  return tr;
}

function render(){
  var termo = String($("#busca").val() || "").trim().toLowerCase();
  var lista = ordenar(filtrar(termo));

  $("#resumo").text(
    lista.length === MAPAS.length
      ? MAPAS.length + (MAPAS.length === 1 ? " mapa" : " mapas")
      : lista.length + " de " + MAPAS.length + " mapas"
  );

  var tabela = $("#tabela").empty();
  if(lista.length === 0){
    tabela.append($("<p class='aviso' style='padding:20px'>").text(
      termo ? "Nenhum mapa encontrado para “" + termo + "”." : "Nenhum mapa neste domain."
    ));
    return;
  }
  var tbody = $("<tbody>");
  lista.forEach(function(m){ tbody.append(linha(m)); });
  tabela.append($("<table>").append(montarCabecalho()).append(tbody));
}

$("#busca").on("input", render);
$("#ordem").on("change", function(){
  ordem.campo = this.value;
  ordem.desc = padraoDesc( COLUNAS.filter(function(x){ return x.campo === ordem.campo; })[0] );
  render();
});

$.ajax({
  url : "../../service/relationship_list.php",
  data : { domain : DOMAIN },
  success : function(result){
    var js = (typeof result === "string") ? JSON.parse(result) : result;
    MAPAS = js.mapas || [];
    $("#cab").append($("<span class='chip'>").text("domain: " + DOMAIN));
    render();
  },
  error : function(xhr){
    var motivo = "HTTP " + xhr.status;
    try {
      var js = JSON.parse(xhr.responseText);
      if(js && js.error){ motivo = js.error; }
    } catch(e) { }
    $("#tabela").append($("<p class='aviso' style='padding:20px'>").text("Não foi possível carregar a lista: " + motivo));
  }
});
</script>

</body>
</html>
