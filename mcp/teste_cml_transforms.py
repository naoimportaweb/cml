#!/usr/bin/env python3
"""Teste de ponta a ponta do servidor MCP cml-transforms, falando o protocolo por stdin/stdout.

Reexecutável: monta transforms de teste num diretório temporário (fora de app/transform/) e
aponta o servidor para ele com CML_TX_RAIZ; o cache e o log também vão para um temporário
(CML_TX_CACHE), então nada toca no ~/.cml_cache real. Não usa rede nem LLM.

    python3 mcp/teste_cml_transforms.py
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap

AQUI = os.path.dirname(os.path.abspath(__file__))
SERVIDOR = os.path.join(AQUI, "cml_transforms.py")
SEGREDO = "SEGREDO-NAO-PODE-VAZAR-123"

TRANSFORM_ECO = textwrap.dedent('''
    from transform.nucleo import Resultado

    class Eco:
        def executar(self, entrada, ctx):
            r = Resultado()
            r.entidade("e1", entrada["text_label"] + " Ltda", etype="organization",
                       referencias=[ctx.ref("Fonte de teste", "https://exemplo.test/a")])
            r.entidade("e2", "", etype="other")          # sem nome: o validar() descarta
            r.vinculo("ENTRADA", "e1", "controla")
            r.vinculo("ENTRADA", "inexistente", "x")      # ponta solta: descartado
            print("lixo no stdout do transform")         # não pode corromper o protocolo
            return r
''')
TRANSFORM_LENTO = textwrap.dedent('''
    import time
    from transform.nucleo import Resultado

    class Lento:
        def executar(self, entrada, ctx):
            time.sleep(60)
            return Resultado()
''')
TRANSFORM_GRANDE = textwrap.dedent('''
    from transform.nucleo import Resultado

    class Grande:
        def executar(self, entrada, ctx):
            r = Resultado()
            for i in range(150):
                r.entidade("k%d" % i, "Entidade %d" % i, description="x" * 3000,
                           referencias=[ctx.ref("t", "https://exemplo.test/%d" % i)])
                r.vinculo("ENTRADA", "k%d" % i, "liga")
            return r
''')


def cfg(id_, classe, entrada, ttl=0):
    return {"id": id_, "nome": "Teste " + id_, "versao": "1", "entrada": entrada, "saida": ["organization"],
            "fonte": "base-propria", "rede": False, "ttl": ttl, "path": "transform.py", "class": classe}


def criar(raiz, nome, config, codigo):
    pasta = os.path.join(raiz, "base_propria", nome)
    os.makedirs(pasta)
    json.dump(config, open(os.path.join(pasta, "config.json"), "w"))
    open(os.path.join(pasta, "transform.py"), "w").write(codigo)


class Cliente:
    def __init__(self, ambiente):
        self.p = subprocess.Popen([sys.executable, SERVIDOR], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, env=ambiente)
        self.n = 0

    def chamar(self, metodo, params=None):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": metodo, "params": params or {}}) + "\n")
        self.p.stdin.flush()
        resp = json.loads(self.p.stdout.readline())
        assert resp["id"] == self.n, resp
        return resp

    def ferramenta(self, nome, args=None):
        r = self.chamar("tools/call", {"name": nome, "arguments": args if args is not None else {}})
        res = r["result"]
        return res["content"][0]["text"], bool(res.get("isError"))

    def fechar(self):
        self.p.stdin.close()
        self.p.wait(timeout=10)


falhas = []


def confere(nome, condicao, detalhe=""):
    print(("  ok   " if condicao else "  FALHA ") + nome + ("" if condicao else "  -> " + str(detalhe)[:300]))
    if not condicao:
        falhas.append(nome)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        raiz, cache = os.path.join(tmp, "transforms"), os.path.join(tmp, "cache")
        os.makedirs(raiz)
        criar(raiz, "eco", cfg("teste.eco", "Eco", ["person", "other:dominio"], ttl=300), TRANSFORM_ECO)
        criar(raiz, "lento", cfg("teste.lento", "Lento", ["person"]), TRANSFORM_LENTO)
        criar(raiz, "grande", cfg("teste.grande", "Grande", ["organization"]), TRANSFORM_GRANDE)

        amb = dict(os.environ, CML_TX_RAIZ=raiz, CML_TX_CACHE=cache, ROLHAMA_BDD_KEY=SEGREDO,
                   CML_LLM_BACKEND="rolhama")
        c = Cliente(amb)
        try:
            print("protocolo")
            r = c.chamar("initialize", {"protocolVersion": "2025-06-18"})
            confere("initialize devolve serverInfo", r["result"]["serverInfo"]["name"] == "cml-transforms", r)
            nomes = [t["name"] for t in c.chamar("tools/list")["result"]["tools"]]
            confere("tools/list tem as 5 ferramentas", sorted(nomes) == sorted(
                ["listar_transforms", "executar_transform", "ver_log", "limpar_cache", "backend_status"]), nomes)
            confere("ferramenta desconhecida é erro de protocolo",
                    "error" in c.chamar("tools/call", {"name": "nao_existe", "arguments": {}}))

            print("listar_transforms")
            t, err = c.ferramenta("listar_transforms")
            ids = [x["id"] for x in json.loads(t)["transforms"]]
            confere("lista os 3 transforms de teste", sorted(ids) == ["teste.eco", "teste.grande", "teste.lento"], ids)
            t, err = c.ferramenta("listar_transforms", {"etype": "organization"})
            confere("filtra por etype", [x["id"] for x in json.loads(t)["transforms"]] == ["teste.grande"], t)
            t, err = c.ferramenta("listar_transforms", {"etype": "other", "sub_etype": "Domínio"})
            confere("sub_etype casa sem acento/caixa", [x["id"] for x in json.loads(t)["transforms"]] == ["teste.eco"], t)
            t, err = c.ferramenta("listar_transforms", {"etype": "marciano"})
            confere("etype inválido dá erro limpo", err and t.startswith("ERRO:"), t)

            print("executar_transform")
            args = {"id": "teste.eco", "text_label": "Acme", "etype": "person"}
            t, err = c.ferramenta("executar_transform", args)
            r1 = json.loads(t) if not err else {}
            confere("executa e devolve proposta", not err and r1.get("proposta_somente") is True, t)
            confere("entidade válida vem, a sem nome é descartada",
                    [e["text_label"] for e in r1.get("entidades", [])] == ["Acme Ltda"], r1)
            confere("vínculo com ponta solta é descartado", len(r1.get("vinculos", [])) == 1, r1)
            confere("avisos registram os descartes", len(r1.get("avisos", [])) >= 2, r1.get("avisos"))
            confere("1ª execução não veio do cache", r1.get("do_cache") is False, r1)
            t, err = c.ferramenta("executar_transform", args)
            confere("2ª execução vem do cache", not err and json.loads(t).get("do_cache") is True, t)

            print("argumentos inválidos")
            casos = [
                ("transform inexistente", {"id": "nao.existe", "text_label": "x", "etype": "person"}),
                ("etype não aceito pelo transform", {"id": "teste.eco", "text_label": "x", "etype": "organization"}),
                ("etype inválido", {"id": "teste.eco", "text_label": "x", "etype": "xyz"}),
                ("text_label ausente", {"id": "teste.eco", "etype": "person"}),
                ("text_label não é texto", {"id": "teste.eco", "text_label": 5, "etype": "person"}),
                ("urls não é lista", {"id": "teste.eco", "text_label": "x", "etype": "person", "urls": "http://a"}),
                ("url sem http", {"id": "teste.eco", "text_label": "x", "etype": "person", "urls": ["ftp://a"]}),
                ("idioma inválido", {"id": "teste.eco", "text_label": "x", "etype": "person", "idioma": "klingon"}),
                ("timeout fora da faixa", {"id": "teste.eco", "text_label": "x", "etype": "person", "timeout": 99999}),
                ("timeout booleano", {"id": "teste.eco", "text_label": "x", "etype": "person", "timeout": True}),
            ]
            for nome, a in casos:
                t, err = c.ferramenta("executar_transform", a)
                confere(nome + " → erro limpo", err and t.startswith("ERRO:") and "Traceback" not in t, t)
            r = c.chamar("tools/call", {"name": "executar_transform", "arguments": "texto"})
            confere("'arguments' que não é objeto → erro limpo", r["result"].get("isError") is True, r)

            print("timeout (≈5s)")
            t, err = c.ferramenta("executar_transform", {"id": "teste.lento", "text_label": "x", "etype": "person", "timeout": 5})
            confere("transform travado é interrompido", err and "tempo esgotado" in t, t)
            t, err = c.ferramenta("backend_status")
            confere("servidor segue respondendo depois do timeout", not err, t)

            print("saída grande")
            t, err = c.ferramenta("executar_transform", {"id": "teste.grande", "text_label": "G", "etype": "organization"})
            g = json.loads(t) if not err else {}
            confere("saída cortada continua JSON válido e dentro do limite", not err and len(t) <= 70_000, len(t))
            confere("corte é avisado", any("cortada" in a for a in g.get("avisos", [])), g.get("avisos"))
            chaves = {e["chave"] for e in g.get("entidades", [])} | {"ENTRADA"}
            confere("sem vínculo de ponta solta após o corte",
                    all(v["para"] in chaves for v in g.get("vinculos", [])), "")

            print("ver_log")
            t, err = c.ferramenta("ver_log", {"n": 5})
            linhas = [json.loads(l) for l in t.splitlines()]
            confere("log tem as execuções (ok, cache, erro)", not err and {"ok", "cache"} <= {l["situacao"] for l in linhas}, t)
            confere("n respeitado", len(linhas) <= 5, len(linhas))
            t, err = c.ferramenta("ver_log", {"n": 0})
            confere("n=0 → erro limpo", err and t.startswith("ERRO:"), t)

            print("backend_status")
            t, err = c.ferramenta("backend_status")
            confere("não vaza valor do ambiente", not err and SEGREDO not in t, t)
            confere("diz SIM para a chave definida", json.loads(t)["ROLHAMA_BDD_KEY_definida"] == "SIM", t)

            print("limpar_cache")
            t, err = c.ferramenta("limpar_cache", {"transform_id": ".."})
            confere("transform_id '..' recusado", err, t)
            t, err = c.ferramenta("limpar_cache", {"transform_id": "teste.eco"})
            confere("apaga o cache de um transform", not err and t.startswith("1 entrada"), t)
            confere("o log permanece", os.path.exists(os.path.join(cache, "transform.log")), "")
            t, err = c.ferramenta("executar_transform", args)
            confere("depois de limpar, não vem do cache", json.loads(t).get("do_cache") is False, t)
            # link simbólico para fora do cache nunca é seguido
            fora = os.path.join(tmp, "fora")
            os.makedirs(fora)
            alvo = os.path.join(fora, "precioso.json")
            open(alvo, "w").write("{}")
            os.symlink(fora, os.path.join(cache, "intruso"))
            t, err = c.ferramenta("limpar_cache")
            confere("link simbólico não é seguido", os.path.exists(alvo), t)
        finally:
            c.fechar()

    print()
    if falhas:
        print("FALHARAM %d: %s" % (len(falhas), "; ".join(falhas)))
        return 1
    print("tudo passou")
    return 0


if __name__ == "__main__":
    sys.exit(main())
