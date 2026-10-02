#!/usr/bin/env python3
"""Teste de integracao dos transforms de OSINT (api_aberta/*). Python puro, SEM Qt, usa a REDE
de verdade e nenhuma chave: os que exigem chave so conferem que falham com a mensagem certa.

    python3 app/transform/testes_osint.py            # todos
    python3 app/transform/testes_osint.py dns crtsh  # so os ids que contenham esses trechos

Cache e log vao para um diretorio temporario (nao suja ~/.cml_cache). Fontes publicas
oscilam (crt.sh, GDELT limitam uso): falha de rede aparece como AVISO, falha de contrato como ERRO.
"""

import os, sys, json, tempfile, time, inspect;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( CURRENTDIR ) );

from transform.nucleo import Registro, Executor, ErroTransform, ENTRADA, env;
from transform.contexto import Contexto;

# id do transform -> entrada. O que nao tem entrada aqui nao e testado (e acusado no fim).
def E(nome, etype="other", **kw):
    d = {"id": None, "text_label": nome, "etype": etype, "sub_etype": "", "small_label": "", "description": "",
         "wikipedia": None, "default_url": None, "urls": [], "idioma": "pt-BR"};
    d.update(kw);
    return d;

CASOS = {
    "wikidata.relacionados":  E("Petrobras", "organization"),
    "crtsh.subdominios":      E("example.com"),
    "dns.registros":          E("example.com"),
    "rdap.registro":          E("example.com"),
    "internetdb.exposicao":   E("8.8.8.8"),
    "brasilapi.cnpj":         E("Banco do Brasil", "organization", description="CNPJ 00.000.000/0001-91"),
    "brasilapi.cep":          E("Praça da Sé", description="CEP 01001-000"),
    "wayback.historico":      E("example.com"),
    "abusech.urlhaus_threatfox": E("example.com"),   # sem chave: tem que falhar com a mensagem da chave
    "otx.reputacao":          E("8.8.8.8"),
    "urlscan.varreduras":     E("example.com"),
    "github.perfil":          E("Linus Torvalds", "person", default_url="https://github.com/torvalds"),
    "gravatar.perfil":        E("beau@dentedreality.com.au"),
    "ripestat.rede":          E("8.8.8.8"),
    "gdelt.noticias":         E("Petrobras", "organization"),
    "nominatim.lugar":        E("Faculdade de Tecnologia da Zona Leste"),
    "virustotal.relacoes":    E("example.com"),      # sem chave
    "hunter.emails":          E("example.com"),      # sem chave
};
EXIGEM_CHAVE = {"abusech.urlhaus_threatfox": "CML_TX_ABUSECH_KEY", "virustotal.relacoes": "CML_TX_VIRUSTOTAL_KEY", "hunter.emails": "CML_TX_HUNTER_KEY"};


def main():
    filtros = sys.argv[1:];
    ex = Executor(dir_cache=tempfile.mkdtemp(prefix="cml_tx_"));
    reg = Registro();
    cfgs = [c for c in reg.todos() if c["_dir"].find(os.sep + "api_aberta" + os.sep) >= 0];
    for e in reg.erros:
        print("ERRO de config:", e);
    ok = erro = aviso = 0;
    for cfg in cfgs:
        if filtros and not any(f in cfg["id"] for f in filtros):
            continue;
        entrada = CASOS.get(cfg["id"]);
        print("\n=== %s (%s)" % (cfg["id"], entrada["text_label"] if entrada else "SEM CASO"));
        if entrada == None:
            print("  ERRO: sem caso de teste."); erro += 1; continue;
        t0 = time.time();
        try:
            r, _cache = ex.executar(cfg, entrada, lambda c: Contexto(c));
        except ErroTransform as e:
            chave = EXIGEM_CHAVE.get(cfg["id"]);
            if chave and not env(chave):
                if chave in str(e):
                    print("  ok (sem chave): %s" % e); ok += 1;
                else:
                    print("  ERRO: falhou sem citar %s: %s" % (chave, e)); erro += 1;
            else:
                print("  AVISO (fonte/rede): %s" % e); aviso += 1;
            continue;
        except Exception as e:
            print("  ERRO: %s: %s" % (type(e).__name__, e)); erro += 1; continue;
        print("  %d entidade(s), %d vínculo(s) em %.1fs" % (len(r.entidades), len(r.vinculos), time.time() - t0));
        for e in r.entidades[:6]:
            print("   · [%s%s] %s — %s" % (e["etype"], ":" + e["sub_etype"] if e["sub_etype"] else "", e["text_label"][:60], e["description"][:70]));
        chaves = {e["chave"] for e in r.entidades} | {ENTRADA};
        for v in r.vinculos[:4]:
            print("   → %s -[%s%s]-> %s" % (v["de"], v["verbo"], " " + str(v["start_date"]) if v["start_date"] else "", v["para"]));
        for a in r.avisos[:4]:
            print("   ! " + a);
        # contrato: tudo com fonte, nenhuma ponta solta, nenhuma data suja
        sem_ref = [e["text_label"] for e in r.entidades if not e["referencias"]];
        soltas = [v for v in r.vinculos if v["de"] not in chaves or v["para"] not in chaves];
        sujas = [v for v in r.vinculos if v["start_date"] and len(v["start_date"]) != 10];
        if sem_ref or soltas or sujas:
            print("  ERRO de contrato: sem_ref=%s soltas=%d sujas=%d" % (sem_ref[:3], len(soltas), len(sujas))); erro += 1;
        elif not r.entidades and not r.avisos:
            print("  ERRO: resultado vazio e sem aviso"); erro += 1;
        else:
            ok += 1;
    print("\nResumo: %d ok, %d aviso(s) de fonte, %d erro(s)." % (ok, aviso, erro));
    return 1 if erro else 0;


if __name__ == "__main__":
    sys.exit(main());
