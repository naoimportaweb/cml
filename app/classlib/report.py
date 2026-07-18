"""Geracao do report em PDF de um mapa de vinculos.

Fluxo: coleta as referencias do mapa -> le os links (ate MAX_REFERENCIAS) -> monta um
prompt unico com a estrutura do mapa + os textos -> rolhama/ollama -> PDF -> anexa.

Por que UM prompt e nao um por referencia: o worker do rolhama e concentrador de thread
unica e serializa globalmente, entao cada chamada segura a fila de todos os projetos.
Um report = uma geracao.

Por que o corte em 50: o prompt inteiro tem que caber na janela de contexto do modelo (o
teto de 64 MiB do transporte webapi e folgado demais para servir de limite). Com 50
referencias, o ORCAMENTO_TEXTO derivado do NUM_CTX vira o teto por referencia
(MAX_POR_REFERENCIA). O que passa do corte nao some — vai listado em "Demais referencias"
no fim do PDF.
"""

import os, sys, inspect, re, html, datetime;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( CURRENTDIR ) );

import requests;
from bs4 import BeautifulSoup;

from classlib.rolhama import Rolhama, BLOB_MAX, _env;
from classlib.document import Document;

# Teto de referencias lidas pelo LLM. As demais entram na lista do fim do PDF.
MAX_REFERENCIAS = 50;

# O que limita o prompt NAO e o teto do transporte (64 MiB no webapi): e a janela de
# contexto do modelo, muito menor. Estourar a janela nao da erro — o ollama trunca o prompt
# em SILENCIO e o modelo responde confiante sobre o pedaco que viu. Tem que casar com o
# ROLHAMA_OLLAMA_NUM_CTX do .env da maquina 90; se divergir, quem manda e o worker.
NUM_CTX = int( _env("ROLHAMA_OLLAMA_NUM_CTX", "16384") );

# Modelo pedido por request (Forma B do SPEC). Tem que ser a TAG EXATA do
# ROLHAMA_OLLAMA_MODEL da 90 — hoje "qwen2.5:14b-instruct". Pedir uma tag diferente (ex.:
# "qwen2.5:14b") faria o ollama baixar outros 9GB e, com OLLAMA_MAX_LOADED_MODELS=1,
# descarregar/carregar modelo a cada alternancia com os outros projetos. Pedir a mesma tag
# do padrao nao troca nada e deixa registrado no PDF qual modelo escreveu o relatorio.
MODELO = _env("CML_REPORT_MODELO", "qwen2.5:14b-instruct");

TOKENS_SAIDA     = 2000;   # espaco reservado para a resposta dentro da mesma janela
TOKENS_ESTRUTURA = 1500;   # instrucoes + entidades e vinculos do mapa
CHARS_POR_TOKEN  = 3.5;    # conservador para pt-BR: acentuado custa mais token

_tokens_refs = max(1000, NUM_CTX - TOKENS_SAIDA - TOKENS_ESTRUTURA);
ORCAMENTO_TEXTO    = int(_tokens_refs * CHARS_POR_TOKEN);
MAX_POR_REFERENCIA = ORCAMENTO_TEXTO // MAX_REFERENCIAS;

TIMEOUT_HTTP = 20;
UA = "Mozilla/5.0 (compatible; CML/1.0; +https://github.com/naoimportaweb/cml)";

ROTULO = {"person": "Pessoa", "organization": "Organização", "other": "Outro", "link": "Vínculo"};


def _texto_da_pagina(url):
    """Baixa a URL e devolve o texto legivel. Nunca lanca: erro vira a propria mensagem."""
    try:
        r = requests.get(url, timeout=TIMEOUT_HTTP, headers={"User-Agent": UA});
        if r.status_code != 200:
            return None, "HTTP " + str(r.status_code);
        tipo = r.headers.get("Content-Type", "");
        if "html" not in tipo and "text" not in tipo:
            return None, "tipo não textual (" + tipo.split(";")[0] + ")";
        sopa = BeautifulSoup(r.text, "html.parser");
        for tag in sopa(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
            tag.decompose();
        texto = re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]{2,}", " ", sopa.get_text("\n")));
        texto = texto.strip();
        if texto == "":
            return None, "página sem texto";
        return texto, None;
    except Exception as e:
        return None, type(e).__name__;


def coletar_referencias(mapa):
    """Junta as referencias das entidades do mapa, sem repetir a mesma referencia."""
    vistos = set();
    saida = [];
    for element in mapa.elements:
        entidade = element.entity;
        for ref in entidade.references:
            chave = (ref.link1 or "").strip();
            if chave == "" or chave in vistos:
                continue;
            vistos.add(chave);
            # A classe Reference (classlib/relationship/entitys.py) guarda em .description;
            # 'descricao' e o nome do campo no JSON do servidor, nao no objeto do cliente.
            saida.append({"title": ref.title, "link": chave, "descricao": ref.description,
                          "entidade": entidade.text, "etype": entidade.etype});
    return saida;


def descrever_mapa(mapa):
    """Estrutura do mapa em texto: e o contexto que o modelo precisa alem dos artigos."""
    linhas = ["MAPA: " + str(mapa.name)];
    if mapa.keyword:
        linhas.append("PALAVRAS-CHAVE: " + str(mapa.keyword));
    linhas.append("");
    linhas.append("ENTIDADES:");
    for e in mapa.elements:
        if e.entity.etype == "link":
            continue;
        d = (e.entity.full_description or "").strip().replace("\n", " ");
        linhas.append("- " + str(e.entity.text) + " [" + ROTULO.get(e.entity.etype, e.entity.etype) + "]" +
                      (": " + d[:300] if d else ""));
    linhas.append("");
    linhas.append("VÍNCULOS (origem -> vínculo -> destino):");
    for e in mapa.elements:
        if e.entity.etype != "link":
            continue;
        # to_entity/from_entity guardam LinkEntity, nao a caixa: LinkEntity.entity e a
        # CAIXA (Person/Organization/Other), que por sua vez tem .entity com a Entity. Sao
        # tres niveis; getText() da caixa resolve os dois ultimos.
        origens  = [ str(x.entity.getText()) for x in e.from_entity ];
        destinos = [ str(x.entity.getText()) for x in e.to_entity ];
        linhas.append("- " + ", ".join(origens) + " -> " + str(e.entity.text) + " -> " + ", ".join(destinos));
    return "\n".join(linhas);


def montar_prompt(mapa, lidas):
    partes = [
        "Você é um analista de inteligência. Escreva um relatório em português do Brasil "
        "sobre o mapa de vínculos abaixo, usando SOMENTE o que está no mapa e nos artigos "
        "fornecidos. Não invente fatos, datas nem nomes. Se algo não estiver nas fontes, "
        "diga que não foi possível confirmar.",
        "",
        "Estruture assim: 1) Sumário executivo; 2) Entidades e papéis; 3) Vínculos e o que "
        "as fontes sustentam; 4) Lacunas e contradições entre as fontes.",
        "",
        "=== ESTRUTURA DO MAPA ===",
        descrever_mapa(mapa),
        "",
        "=== ARTIGOS DAS REFERÊNCIAS ===",
    ];
    for i, ref in enumerate(lidas, 1):
        partes.append("");
        partes.append("--- [" + str(i) + "] " + str(ref["title"]) + " (" + ref["link"] + ") ---");
        partes.append(ref["texto"]);
    return "\n".join(partes);


def gerar(mapa, caminho_pdf, progresso=None):
    """Le as referencias, gera o texto no rolhama e escreve o PDF. Devolve um resumo."""
    def aviso(msg):
        if progresso != None:
            progresso(msg);

    todas = coletar_referencias(mapa);
    alvo  = todas[:MAX_REFERENCIAS];
    demais = todas[MAX_REFERENCIAS:];

    lidas, falhas = [], [];
    for i, ref in enumerate(alvo, 1):
        aviso("Lendo referência %d/%d: %s" % (i, len(alvo), (ref["title"] or ref["link"])[:60]));
        texto, erro = _texto_da_pagina(ref["link"]);
        if texto == None:
            falhas.append({"ref": ref, "erro": erro});
            continue;
        if len(texto) > MAX_POR_REFERENCIA:
            texto = texto[:MAX_POR_REFERENCIA] + "\n[...texto truncado...]";
        ref = dict(ref); ref["texto"] = texto;
        lidas.append(ref);

    if len(lidas) == 0:
        raise Exception("Nenhuma das %d referências pôde ser lida." % len(alvo));

    prompt = montar_prompt(mapa, lidas);

    # Duas guardas, e a que importa e a primeira: o ollama corta o prompt na janela sem
    # avisar, entao um prompt grande demais nao falha — ele mente. Melhor derrubar
    # referencia aqui, contando quantas, do que entregar relatorio baseado no comeco.
    teto_chars = int((NUM_CTX - TOKENS_SAIDA) * CHARS_POR_TOKEN);
    derrubadas = 0;
    while len(prompt) > teto_chars and len(lidas) > 1:
        demais.insert(0, lidas.pop());   # o que sai da leitura vai para "Demais referencias"
        derrubadas = derrubadas + 1;
        prompt = montar_prompt(mapa, lidas);
    if derrubadas > 0:
        aviso("%d referência(s) não couberam na janela de %d tokens e foram para “Demais referências”." % (derrubadas, NUM_CTX));

    if len(prompt.encode("utf-8")) > BLOB_MAX:
        raise Exception("O prompt tem %d bytes e o webapi recusa acima de %d." % (len(prompt.encode("utf-8")), BLOB_MAX));

    aviso("Gerando o relatório no rolhama (%s; pode levar minutos, o worker atende um por vez)…" % MODELO);
    r = Rolhama();
    texto_report = r.gerar(prompt, model=MODELO);

    aviso("Montando o PDF…");
    escrever_pdf(caminho_pdf, mapa, texto_report, lidas, demais, falhas);

    return {"lidas": len(lidas), "falhas": len(falhas), "demais": len(demais),
            "total": len(todas), "canal": r.canal, "pdf": caminho_pdf};


def _h(s):
    return html.escape(str(s if s != None else ""));


def _inline(texto):
    """**negrito**, *italico* e `codigo` -> HTML. Escapa ANTES de injetar as tags, senao
    um '<' vindo do modelo viraria marcacao."""
    t = _h(texto);
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t);
    t = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"<i>\1</i>", t);
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t);
    return t;


def markdown_para_html(texto):
    """Converte o Markdown que o modelo produz. Nao e um parser completo: cobre titulo,
    lista e negrito, que e o que o ollama emite nesses relatorios. Sem isto os '###' e os
    '**' apareciam crus no PDF.

    Trabalha por BLOCO, nao por linha: em Markdown uma quebra simples dentro de um bloco e
    quebra suave e continua o mesmo paragrafo/item. Um parser linha-a-linha jogava a
    continuacao de um item para fora da lista, na margem.
    """
    saida = [];
    lista = None;     # 'ol' | 'ul' | None
    buffer = [];      # linhas do item/paragrafo corrente

    def fecha_buffer():
        if not buffer:
            return;
        texto_junto = " ".join(buffer);
        if lista == "ol":
            # O modelo enfileira "1. a 2. b 3. c" e ainda quebra no meio. Separar so aqui,
            # com as continuacoes ja remontadas, e o que faz o "2." que caiu numa linha de
            # continuacao virar item proprio.
            for parte in re.split(r"(?<=[.:;)])\s+(?=\d+\.\s)", texto_junto):
                parte = re.sub(r"^\d+\.\s+", "", parte.strip());
                if parte:
                    saida.append("<li>" + _inline(parte) + "</li>");
        elif lista == "ul":
            saida.append("<li>" + _inline(texto_junto) + "</li>");
        else:
            saida.append("<p>" + _inline(texto_junto) + "</p>");
        del buffer[:];

    def fecha_lista():
        fecha_buffer();
        if lista != None:
            saida.append("</" + lista + ">");

    def abre_lista(tipo):
        nonlocal lista;
        fecha_buffer();
        if lista != tipo:
            if lista != None:
                saida.append("</" + lista + ">");
            saida.append("<" + tipo + ">");
            lista = tipo;

    for linha in str(texto).replace("\r", "").split("\n"):
        s = linha.strip();

        if s == "":
            fecha_lista(); lista = None;
            continue;

        t = re.match(r"^(#{1,6})\s+(.*)$", s);
        if t:
            fecha_lista(); lista = None;
            nivel = min(len(t.group(1)) + 1, 4);   # ### do modelo -> h4 no PDF
            saida.append("<h%d>%s</h%d>" % (nivel, _inline(t.group(2)), nivel));
            continue;

        # "1. item": guarda a linha inteira, prefixo e tudo — quem separa e o fecha_buffer,
        # depois de juntar as continuacoes.
        if re.match(r"^\d+\.\s+", s):
            abre_lista("ol");
            fecha_buffer();
            buffer.append(s);
            continue;

        if re.match(r"^[-*+]\s+", s):
            abre_lista("ul");
            fecha_buffer();
            buffer.append( re.sub(r"^[-*+]\s+", "", s) );
            continue;

        # Linha sem marcador: e continuacao (quebra suave) do item/paragrafo corrente.
        buffer.append(s);

    fecha_lista();
    return "".join(saida);


def escrever_pdf(caminho, mapa, texto_report, lidas, demais, falhas):
    """Monta o PDF com QTextDocument -> QPdfWriter (ambos ja vem no PySide6)."""
    from PySide6.QtGui import QPdfWriter, QTextDocument, QPageSize;
    from PySide6.QtCore import QMarginsF, QSizeF;

    corpo = [];
    corpo.append("<h1>" + _h(mapa.name) + "</h1>");
    if mapa.keyword:
        corpo.append("<p style='color:#555'>" + _h(mapa.keyword) + "</p>");
    corpo.append("<p style='color:#888;font-size:9pt'>Gerado por CML em " +
                 datetime.datetime.now().strftime("%d/%m/%Y %H:%M") +
                 " · texto produzido por modelo de linguagem a partir das referências listadas</p>");
    corpo.append("<hr>");

    corpo.append( markdown_para_html( texto_report ) );

    corpo.append("<h2>Referências utilizadas (" + str(len(lidas)) + ")</h2><ol>");
    for ref in lidas:
        corpo.append("<li>" + _h(ref["title"]) + "<br><span style='color:#555;font-size:9pt'>" +
                     _h(ref["link"]) + "</span></li>");
    corpo.append("</ol>");

    if len(falhas) > 0:
        # Um link que nao abriu nao entrou no relatorio: dizer isso e o que separa
        # "nao havia informacao" de "a fonte estava fora do ar".
        corpo.append("<h2>Referências que não puderam ser lidas (" + str(len(falhas)) + ")</h2><ul>");
        for f in falhas:
            corpo.append("<li>" + _h(f["ref"]["title"]) + " — " + _h(f["erro"]) +
                         "<br><span style='color:#555;font-size:9pt'>" + _h(f["ref"]["link"]) + "</span></li>");
        corpo.append("</ul>");

    if len(demais) > 0:
        # O corte em MAX_REFERENCIAS nao pode ser silencioso: quem le o relatorio precisa
        # saber que existe fonte que o modelo nao viu.
        corpo.append("<h2>Demais referências (" + str(len(demais)) + ")</h2>");
        corpo.append("<p style='color:#555;font-size:9pt'>Não foram lidas pelo modelo: o "
                     "relatório usa no máximo " + str(MAX_REFERENCIAS) + " referências.</p><ul>");
        for ref in demais:
            corpo.append("<li>" + _h(ref["title"]) + "<br><span style='color:#555;font-size:9pt'>" +
                         _h(ref["link"]) + "</span></li>");
        corpo.append("</ul>");

    escritor = QPdfWriter(caminho);
    escritor.setPageSize(QPageSize(QPageSize.A4));
    # setResolution(96) e obrigatorio: o QPdfWriter nasce em 1200 DPI e o width()/height()
    # saem em pixels dessa densidade, mas o QTextDocument diagrama na convencao de 96 —
    # sem isto o texto sai microscopico num canto da pagina. Verificado rasterizando.
    escritor.setResolution(96);
    escritor.setPageMargins(QMarginsF(18, 18, 18, 18));
    escritor.setTitle(str(mapa.name));

    doc = QTextDocument();
    doc.setHtml("<html><body style=\"font-family:sans-serif;font-size:10pt\">" + "".join(corpo) + "</body></html>");
    doc.setPageSize(QSizeF(escritor.width(), escritor.height()));
    doc.print_(escritor);
    return caminho;
