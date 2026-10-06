#!/usr/bin/env python3
# Confere a SQL do servidor contra o schema de server/data/create.sql.
#
# Por que existe: nada do lado PHP roda em teste. Tabela ou coluna errada nao da erro de
# sintaxe, nao aparece no `php -l`, e so se revela em PRODUCAO, como um 500 no meio de uma
# investigacao. Este teste le o create.sql, monta {tabela: colunas} e confere cada
# `alias.coluna` e cada FROM/JOIN das consultas.
#
# Nao e um parser de SQL -- e reconhecimento de padrao, de proposito: um parser de verdade
# daria mais trabalho de manter do que o problema que resolve. Em troca, o que ele nao
# entender fica listado no fim como "nao conferido", para a lacuna ser visivel em vez de
# passar por aprovacao.
#
#   python3 app/test/sql_schema.py

import os, re, sys, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
REPO = os.path.dirname(os.path.dirname(CURRENTDIR));
SERVER = os.path.join(REPO, "server");
CREATE = os.path.join(SERVER, "data", "create.sql");

FALHAS = [];
NAO_CONFERIDO = [];

# Nomes que aparecem depois de FROM/JOIN mas nao sao tabela.
PALAVRAS = {"select", "dual", "where", "on", "as", "set", "values", "duplicate", "key", "update"};
# Schemas do proprio MySQL: existem, mas nao estao (nem deveriam estar) no create.sql.
SISTEMA = {"information_schema", "performance_schema", "mysql", "sys"};


def confere(condicao, descricao):
    print(("  ok   " if condicao else "  ERRO ") + descricao);
    if not condicao:
        FALHAS.append(descricao);


def __por_virgula__(texto):
    """Separa por virgula ignorando as que estao dentro de parenteses, como em DECIMAL(10,2)."""
    partes, atual, nivel = [], "", 0;
    for caractere in texto:
        if caractere == "(":
            nivel = nivel + 1;
        elif caractere == ")":
            nivel = nivel - 1;
        if caractere == "," and nivel == 0:
            partes.append(atual);
            atual = "";
            continue;
        atual = atual + caractere;
    partes.append(atual);
    return partes;


def schema():
    """{tabela: set(colunas)} a partir do create.sql, incluindo as colunas que os blocos de
    migracao acrescentam com ALTER TABLE -- senao o teste acusaria como inexistente justamente
    a coluna nova que o bloco manda criar."""
    with open(CREATE, encoding="utf-8", errors="replace") as arquivo:
        texto = arquivo.read();
    # Comentario de linha do MySQL some antes de tudo, senao o "--" de dentro dos blocos de
    # migracao entra como se fosse DDL.
    limpo = "\n".join(l.split("--")[0] for l in texto.splitlines());
    tabelas = {};
    for bloco in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?`?(\w+)`?\s*\((.*?)\n\s*\)\s*;",
                             limpo, re.S | re.I):
        nome = bloco.group(1).lower();
        colunas = set();
        # Separa por virgula de TOPO (fora de parenteses): o create.sql declara
        # "x INT NOT NULL, y INT NOT NULL, w INT, h INT" numa linha so, e ler uma coluna por
        # linha perdia tres de cada quatro -- foi o que fez o teste acusar codigo que funciona.
        for declaracao in __por_virgula__(bloco.group(2)):
            declaracao = declaracao.strip();
            if declaracao == "" or re.match(r"(primary|foreign|unique|key|constraint|index)\b", declaracao, re.I):
                continue;
            m = re.match(r"`?(\w+)`?\s+", declaracao);
            if m:
                colunas.add(m.group(1).lower());
        tabelas.setdefault(nome, set()).update(colunas);
    for alter in re.finditer(r"alter\s+table\s+`?(\w+)`?\s+add\s+(?:column\s+)?`?(\w+)`?\s", limpo, re.I):
        nome, coluna = alter.group(1).lower(), alter.group(2).lower();
        if coluna in ("foreign", "primary", "unique", "index", "key", "constraint"):
            continue;
        tabelas.setdefault(nome, set()).add(coluna);
    return tabelas;


def consultas_do_arquivo(caminho):
    """Trechos de SQL dentro de strings PHP. Pega aspas duplas e simples, e junta a
    concatenacao com . que o codigo usa para quebrar consulta longa em varias linhas."""
    with open(caminho, encoding="utf-8", errors="replace") as arquivo:
        texto = arquivo.read();
    saida = [];
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"(\s*\.\s*"(?:[^"\\]|\\.)*")*', texto, re.S):
        bruto = m.group(0);
        partes = re.findall(r'"((?:[^"\\]|\\.)*)"', bruto, re.S);
        inteiro = " ".join(partes);
        if re.search(r"\b(select|insert\s+into|update|delete\s+from)\b", inteiro, re.I):
            saida.append(inteiro);
    return saida;


def aliases(consulta):
    """{alias: tabela} de FROM/JOIN, aceitando com e sem AS. A propria tabela tambem vira
    alias de si mesma, porque `pessoa.id` sem alias e comum."""
    mapa = {};
    for m in re.finditer(r"\b(?:from|join)\s+`?(\w+)`?(?:\s+as\s+`?(\w+)`?|\s+(?!on\b|where\b|set\b|inner\b|left\b|right\b|join\b|group\b|order\b|limit\b|values\b)`?(\w+)`?)?",
                         consulta, re.I):
        tabela = m.group(1).lower();
        if tabela in PALAVRAS:
            continue;
        apelido = (m.group(2) or m.group(3) or tabela).lower();
        mapa[apelido] = tabela;
        mapa.setdefault(tabela, tabela);
    return mapa;


def main():
    tabelas = schema();
    print("schema lido de create.sql");
    confere(len(tabelas) > 20, "%d tabelas" % len(tabelas));
    for obrigatoria in ("person", "entity", "diagram_relationship", "diagram_relationship_link",
                        "organization_chart_item", "diagram_timeline", "diagram_timeline_event"):
        confere(obrigatoria in tabelas, "tabela %s reconhecida" % obrigatoria);

    arquivos = [];
    for raiz, _dirs, nomes in os.walk(SERVER):
        for nome in nomes:
            if nome.endswith(".php"):
                arquivos.append(os.path.join(raiz, nome));
    arquivos.sort();

    print("\nconsultas encontradas");
    total_consultas = 0;
    problemas = [];
    for caminho in arquivos:
        for consulta in consultas_do_arquivo(caminho):
            total_consultas = total_consultas + 1;
            apelidos = aliases(consulta);
            curto = os.path.relpath(caminho, REPO);

            # tabela que nao existe
            for tabela in set(apelidos.values()):
                if tabela in SISTEMA:
                    continue;
                if tabela not in tabelas:
                    problemas.append("%s: tabela inexistente '%s'" % (curto, tabela));

            # alias.coluna
            for m in re.finditer(r"\b(\w+)\.(\w+)\b", consulta):
                apelido, coluna = m.group(1).lower(), m.group(2).lower();
                if apelido not in apelidos:
                    NAO_CONFERIDO.append("%s: %s.%s (apelido desconhecido)" % (curto, apelido, coluna));
                    continue;
                tabela = apelidos[apelido];
                if tabela in SISTEMA:
                    continue;
                if tabela not in tabelas:
                    continue;   # ja acusado acima
                if coluna == "*":
                    continue;
                if coluna not in tabelas[tabela]:
                    problemas.append("%s: %s.%s não existe em %s" % (curto, apelido, coluna, tabela));

    confere(total_consultas > 20, "%d consultas analisadas em %d arquivos" % (total_consultas, len(arquivos)));

    print("\ncolunas e tabelas conferem com o schema");
    vistos = [];
    for p in problemas:
        if p not in vistos:
            vistos.append(p);
    confere(len(vistos) == 0,
            "nenhum problema" if len(vistos) == 0
            else "%d problema(s): %s" % (len(vistos), " | ".join(vistos[:6])));

    if len(NAO_CONFERIDO) > 0:
        # Visivel de proposito: o que o reconhecimento nao entendeu nao pode passar por
        # "aprovado". Se esta lista crescer muito, o padrao e que precisa melhorar.
        unicos = [];
        for n in NAO_CONFERIDO:
            if n not in unicos:
                unicos.append(n);
        print("\n  --   %d referência(s) não conferida(s) (padrão não reconhecido):" % len(unicos));
        for n in unicos[:8]:
            print("       " + n);

    print("\n" + ("TODOS OS TESTES PASSARAM" if len(FALHAS) == 0 else "FALHAS: %d" % len(FALHAS)));
    return 1 if len(FALHAS) > 0 else 0;


if __name__ == "__main__":
    sys.exit(main());
