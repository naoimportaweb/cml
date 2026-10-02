"""Generaliza o bot `entidades`: le ate 3 paginas ligadas a entidade (Wikipedia, site oficial,
referencias) e pede ao LLM as relacoes em que ELA aparece. LLM = ctx.llm() (rolhama canal 510
por padrao; ollama so por opt-in). Um prompt so: o worker serializa globalmente."""

import os, sys, inspect, json;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, norm;

MAX_PAGINAS = 3;
MAX_POR_PAGINA = 4000;
TIPOS = ["person", "organization", "other"];

class TransformExtrair(Transform):
    def executar(self, entrada, ctx):
        from classlib.report import ler_pagina, idioma_frase, instrucao_idioma;
        nome = str(entrada.get("text_label") or "").strip();
        urls = [];
        for u in [entrada.get("wikipedia"), entrada.get("default_url")] + list(entrada.get("urls") or []):
            u = str(u or "").strip();
            if u.lower().startswith(("http://", "https://")) and u not in urls:
                urls.append(u);
        urls = urls[:MAX_PAGINAS];
        if not urls:
            raise ErroTransform("a entidade não tem Wikipedia, site oficial nem referência com URL");

        paginas = [];
        for u in urls:
            texto, titulo, _desc, erro = ler_pagina(u);
            if texto == None:
                continue;
            paginas.append((u, titulo or u, texto[:MAX_POR_PAGINA]));
        if not paginas:
            raise ErroTransform("nenhuma das páginas pôde ser lida");

        codigo = entrada.get("idioma") or "en";
        prompt = ('O foco é "' + nome + '". Extraia dos textos as entidades relacionadas a ele e as relações. '
                  'tipo: person|organization|other. Escreva "descricao" e "relacao" em ' + idioma_frase(codigo) + '.\n'
                  'Responda SOMENTE JSON: {"entidades":[{"nome":"","tipo":"","descricao":""}],'
                  '"vinculos":[{"origem":"","relacao":"","destino":""}]}\n');
        for i, (u, t, texto) in enumerate(paginas):
            prompt += "\nFONTE " + str(i + 1) + " (" + t + "):\n" + texto + "\n";

        saida = ctx.llm().gerar(prompt, formato="json", idioma_instrucao=instrucao_idioma(codigo));
        try:
            js = json.loads(saida);
        except Exception:
            raise ErroTransform("o modelo não devolveu JSON válido — tente de novo");

        refs = [ctx.ref(t, u, "Extraído por IA; confira o tipo e as relações.") for (u, t, _x) in paginas];
        r = Resultado();
        por_nome = {norm(nome): "ENTRADA"};
        def ponta(n):
            n = str(n or "").strip();
            if n == "":
                return None;
            k = norm(n);
            if k in por_nome:
                return por_nome[k];
            chave = "i" + str(len(por_nome));
            r.entidade(chave, n, "other", referencias=refs);     # ponta citada e nao listada: 'other' neutro
            por_nome[k] = chave;
            return chave;
        for e in js.get("entidades") or []:
            n = str(e.get("nome") or "").strip();
            if n == "" or norm(n) in por_nome:
                continue;
            chave = "i" + str(len(por_nome));
            tipo = e.get("tipo") if e.get("tipo") in TIPOS else "other";
            r.entidade(chave, n, tipo, description=str(e.get("descricao") or ""), referencias=refs);
            por_nome[norm(n)] = chave;
        for v in js.get("vinculos") or []:
            de, para = ponta(v.get("origem")), ponta(v.get("destino"));
            if de and para and de != para:
                r.vinculo(de, para, v.get("relacao"), referencias=refs);
        r.aviso("Gerado por IA (%s): o modelo erra tipo e relação — confira antes de aceitar." % ctx.llm().backend);
        return r;
