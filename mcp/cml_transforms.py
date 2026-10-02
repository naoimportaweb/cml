#!/usr/bin/env python3
"""Servidor MCP — transforms do CML (estilo Maltego) expostos ao Claude.

Dá ao Claude o mesmo que o menu de contexto da GUI dá ao analista: listar os transforms que
servem a um tipo de entidade e executar um deles. O que importa saber, em ordem de quanto
custa errar:

- só PROPÕE. `executar_transform` devolve entidades e vínculos candidatos em JSON; nada é
  gravado em mapa, banco ou servidor. Quem decide o que entra é o analista, no painel de
  Proposta da GUI — curadoria humana é o diferencial do CML;
- o transform roda em SUBPROCESSO com timeout (padrão 300s, máx. 900s): fonte externa que
  trava, ou LLM que demora na fila do rolhama, não prende este servidor. Ao estourar o tempo
  o grupo de processos inteiro é morto;
- o núcleo é o mesmo da GUI (`app/transform/nucleo.py` e `contexto.py`, sem Qt): cache, log
  em ~/.cml_cache/transform.log, rota direta/tor e backend de LLM (rolhama por padrão, ollama
  só por opt-in) valem aqui exatamente como lá;
- segredo: o ~/.env da estação nunca é mostrado. `backend_status` e `listar_transforms` só
  dizem SIM/NÃO para "esta variável existe", nunca o valor.

Teste: CML_TX_RAIZ aponta o Registro para outro diretório de transforms e CML_TX_CACHE troca
o ~/.cml_cache. Existem só para o mcp/teste_cml_transforms.py — em uso normal ficam sem definir.

Transporte: stdio, JSON-RPC 2.0. Só stdlib (mais o que o núcleo dos transforms já importa).
"""

import json
import os
import re
import signal
import subprocess
import sys

RAIZ_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ_REPO, "app")
sys.path.insert(0, APP)

LIMITE_SAIDA = 60_000          # bytes devolvidos por chamada
TIMEOUT_PADRAO = 300
TIMEOUT_MAXIMO = 900
MARCA = "@@RESULTADO@@"        # linha do stdout do worker que carrega o JSON final
IDIOMAS = ("pt-BR", "en", "es")  # lista canônica: report.IDIOMAS
MAX_URLS = 10


# --------------------------------------------------------------------------
# Núcleo dos transforms (carregado sob demanda: falha vira erro de ferramenta, não do servidor)
# --------------------------------------------------------------------------
def _nucleo():
    from transform import nucleo
    return nucleo


def _dir_cache() -> str:
    return os.environ.get("CML_TX_CACHE") or _nucleo().DIR_CACHE


def _registro():
    nucleo = _nucleo()
    raiz = os.environ.get("CML_TX_RAIZ")
    return nucleo.Registro(raiz) if raiz else nucleo.Registro()


def _truncar_texto(saida: str) -> str:
    if len(saida) > LIMITE_SAIDA:
        saida = saida[:LIMITE_SAIDA] + f"\n[... truncado em {LIMITE_SAIDA} bytes]"
    return saida


# --------------------------------------------------------------------------
# Validação de argumentos — erro limpo, antes de gastar rede ou fila de LLM
# --------------------------------------------------------------------------
def _texto(args: dict, nome: str, obrigatorio: bool = False, maximo: int = 4000) -> str:
    valor = args.get(nome)
    if valor is None or valor == "":
        if obrigatorio:
            raise ValueError(f"'{nome}' é obrigatório")
        return ""
    if not isinstance(valor, str):
        raise ValueError(f"'{nome}' deve ser texto")
    valor = valor.strip()
    if len(valor) > maximo:
        raise ValueError(f"'{nome}' passa de {maximo} caracteres")
    if obrigatorio and not valor:
        raise ValueError(f"'{nome}' é obrigatório")
    return valor


def _inteiro(args: dict, nome: str, padrao: int, minimo: int, maximo: int) -> int:
    valor = args.get(nome)
    if valor is None:
        return padrao
    # bool é subclasse de int em Python: true não é um número aqui
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"'{nome}' deve ser um inteiro")
    if not minimo <= valor <= maximo:
        raise ValueError(f"'{nome}' deve estar entre {minimo} e {maximo}")
    return valor


def _url_http(valor: str, nome: str) -> str:
    if not re.match(r"^https?://\S+$", valor, re.I):
        raise ValueError(f"'{nome}' deve ser uma URL http(s)")
    return valor


# --------------------------------------------------------------------------
# Ferramentas
# --------------------------------------------------------------------------
def t_listar_transforms(args: dict) -> str:
    nucleo = _nucleo()
    etype = _texto(args, "etype", maximo=40)
    sub_etype = _texto(args, "sub_etype", maximo=100)
    fonte = _texto(args, "fonte", maximo=40)
    if etype and etype not in nucleo.ETYPES:
        raise ValueError(f"'etype' deve ser um de {', '.join(nucleo.ETYPES)}")
    if fonte and fonte not in nucleo.FONTES:
        raise ValueError(f"'fonte' deve ser uma de {', '.join(nucleo.FONTES)}")
    if sub_etype and not etype:
        raise ValueError("'sub_etype' só faz sentido com 'etype'")

    reg = _registro()
    saida = []
    for cfg in reg.todos():
        if etype and not nucleo.aceita(cfg, etype, sub_etype):
            continue
        if fonte and cfg["fonte"] != fonte:
            continue
        chave = cfg.get("chave_env")
        saida.append({
            "id": cfg["id"],
            "nome": cfg["nome"],
            "versao": cfg.get("versao", "1"),
            "fonte": cfg["fonte"],
            "entrada": cfg["entrada"],
            "saida": cfg.get("saida", []),
            "rota": nucleo.rota_efetiva(cfg) if cfg.get("rede") else None,
            "rede": bool(cfg.get("rede")),
            "chave_env": chave,
            # só a presença: o valor mora no ~/.env e não sai daqui
            "chave_env_presente": ("SIM" if nucleo.env(chave) else "NÃO") if chave else None,
            "indisponivel": nucleo.indisponivel(cfg),
        })
    corpo = {"transforms": saida}
    if reg.erros:
        corpo["configs_invalidos"] = reg.erros
    return _truncar_texto(json.dumps(corpo, ensure_ascii=False, indent=2))


def _montar_entrada(args: dict, etype: str) -> dict:
    urls = args.get("urls")
    if urls is None:
        urls = []
    if not isinstance(urls, list) or not all(isinstance(u, str) for u in urls):
        raise ValueError("'urls' deve ser uma lista de textos")
    if len(urls) > MAX_URLS:
        raise ValueError(f"'urls' tem mais de {MAX_URLS} itens")
    urls = [_url_http(u.strip(), "urls[]") for u in urls]

    wikipedia = _texto(args, "wikipedia", maximo=2000)
    default_url = _texto(args, "default_url", maximo=2000)
    if wikipedia:
        _url_http(wikipedia, "wikipedia")
    if default_url:
        _url_http(default_url, "default_url")
    idioma = _texto(args, "idioma", maximo=10) or "pt-BR"
    if idioma not in IDIOMAS:
        raise ValueError(f"'idioma' deve ser um de {', '.join(IDIOMAS)}")

    # mesmas chaves que a GUI entrega ao transform (SPEC §2.2)
    return {
        "id": _texto(args, "entity_id", maximo=128) or None,
        "text_label": _texto(args, "text_label", obrigatorio=True, maximo=250),
        "etype": etype,
        "sub_etype": _texto(args, "sub_etype", maximo=100),
        "small_label": _texto(args, "small_label", maximo=100),
        "description": _texto(args, "description"),
        "wikipedia": wikipedia or None,
        "default_url": default_url or None,
        "urls": urls,
        "idioma": idioma,
    }


def _serial(corpo: dict) -> str:
    return json.dumps(corpo, ensure_ascii=False, indent=2)


def _encolher(corpo: dict) -> dict:
    """Mantém a saída dentro do limite sem quebrar o JSON: corta a cauda de entidades e
    descarta os vínculos que ficaram com ponta solta. Cortar o texto serializado produziria
    JSON inválido, que o cliente não consegue ler."""
    if len(_serial(corpo)) <= LIMITE_SAIDA:
        return corpo
    nucleo = _nucleo()
    total_e, total_v = len(corpo["entidades"]), len(corpo["vinculos"])
    ents = list(corpo["entidades"])
    while ents:
        ents = ents[: max(len(ents) * 3 // 4 - 1, 0)]
        chaves = {e["chave"] for e in ents} | {nucleo.ENTRADA}
        vins = [v for v in corpo["vinculos"] if v["de"] in chaves and v["para"] in chaves]
        candidato = dict(corpo, entidades=ents, vinculos=vins)
        if len(_serial(candidato)) <= LIMITE_SAIDA:
            candidato["avisos"] = list(corpo["avisos"]) + [
                f"Saída cortada para caber em {LIMITE_SAIDA} bytes: {len(ents)} de {total_e} "
                f"entidades e {len(vins)} de {total_v} vínculos."]
            return candidato
    return dict(corpo, entidades=[], vinculos=[], avisos=list(corpo["avisos"]) + [
        f"Saída cortada: nem uma entidade coube em {LIMITE_SAIDA} bytes ({total_e} entidades descartadas)."])


def t_executar_transform(args: dict) -> str:
    nucleo = _nucleo()
    id_ = _texto(args, "id", obrigatorio=True, maximo=120)
    etype = _texto(args, "etype", obrigatorio=True, maximo=40)
    if etype not in nucleo.ETYPES:
        raise ValueError(f"'etype' deve ser um de {', '.join(nucleo.ETYPES)}")
    timeout = _inteiro(args, "timeout", TIMEOUT_PADRAO, 5, TIMEOUT_MAXIMO)
    entrada = _montar_entrada(args, etype)

    cfg = _registro().obter(id_)
    if cfg is None:
        raise ValueError(f"transform '{id_}' não existe (use listar_transforms)")
    if not nucleo.aceita(cfg, etype, entrada["sub_etype"]):
        raise ValueError(f"transform '{id_}' não aceita entrada {etype}"
                         + (f":{entrada['sub_etype']}" if entrada["sub_etype"] else "")
                         + f" (aceita: {', '.join(cfg['entrada'])})")
    motivo = nucleo.indisponivel(cfg)
    if motivo:
        raise RuntimeError(f"transform '{id_}' indisponível: {motivo}")

    resp = _rodar_worker({"id": id_, "entrada": entrada}, timeout)
    if not resp.get("ok"):
        raise RuntimeError(resp.get("erro") or "o transform falhou sem mensagem")
    corpo = dict(resp["resultado"], do_cache=bool(resp.get("do_cache")), proposta_somente=True)
    corpo = _encolher(corpo)
    return _serial(corpo)


def t_ver_log(args: dict) -> str:
    n = _inteiro(args, "n", 20, 1, 200)
    caminho = os.path.join(_dir_cache(), "transform.log")
    try:
        with open(caminho, "rb") as f:
            f.seek(0, os.SEEK_END)
            tam = f.tell()
            f.seek(max(tam - 262_144, 0))   # o fim basta; o log cresce sem rotação
            dados = f.read().decode("utf-8", errors="replace")
    except FileNotFoundError:
        return "[nenhuma execução registrada ainda]"
    linhas = [l for l in dados.splitlines() if l.strip()][-n:]
    return _truncar_texto("\n".join(linhas) if linhas else "[log vazio]")


def t_limpar_cache(args: dict) -> str:
    transform_id = _texto(args, "transform_id", maximo=120)
    raiz = _dir_cache()
    if os.path.islink(raiz):
        raise RuntimeError("o diretório de cache é um link simbólico — recusado")
    if not os.path.isdir(raiz):
        return "[cache inexistente, nada a apagar]"
    raiz_real = os.path.realpath(raiz)

    if transform_id:
        # mesma sanitização do Executor: o nome da pasta de cache é o id com \W trocado por _
        nome = re.sub(r"[^\w.-]", "_", transform_id)
        if nome in (".", "..") or nome.strip(".") == "":
            raise ValueError("'transform_id' inválido")
        alvos = [os.path.join(raiz, nome)]
    else:
        alvos = [os.path.join(raiz, e) for e in sorted(os.listdir(raiz))]

    apagados = 0
    for alvo in alvos:
        if os.path.islink(alvo) or not os.path.isdir(alvo):
            continue   # o transform.log fica; link simbólico nunca é seguido
        real = os.path.realpath(alvo)
        if os.path.commonpath([real, raiz_real]) != raiz_real or real == raiz_real:
            raise RuntimeError(f"caminho fora do cache recusado: {alvo}")
        for pasta, subs, arqs in os.walk(real, followlinks=False):
            for a in arqs:
                p = os.path.join(pasta, a)
                if a.endswith(".json") and not os.path.islink(p):
                    os.unlink(p)
                    apagados += 1
    return f"{apagados} entrada(s) de cache apagada(s) em {raiz}" + (f" ({transform_id})" if transform_id else "")


def t_backend_status(_args: dict) -> str:
    nucleo = _nucleo()
    sim = lambda v: "SIM" if v else "NÃO"
    corpo = {
        "llm_backend": nucleo.backend_llm(),
        "rota_padrao": nucleo.env("CML_TX_ROTA_PADRAO", "direta"),
        "CML_OLLAMA_URL_definida": sim(nucleo.env("CML_OLLAMA_URL")),
        "ROLHAMA_BDD_KEY_definida": sim(nucleo.env("ROLHAMA_BDD_KEY")),
        "CML_CRAUDIO_PORTA_definida": sim(nucleo.env("CML_CRAUDIO_PORTA")),
        "CML_CRAUDIO_PORTA_efetiva": "8765 (padrão)" if not nucleo.env("CML_CRAUDIO_PORTA") else "definida no ~/.env",
        "cache": _dir_cache(),
    }
    return json.dumps(corpo, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------
# Execução isolada: o transform roda em outro processo, com timeout
# --------------------------------------------------------------------------
def _rodar_worker(pedido: dict, timeout: int) -> dict:
    # start_new_session: o worker vira líder de um grupo, e o timeout mata o grupo todo —
    # um transform que dispara processos filhos (curl, navegador) não deixa órfãos.
    p = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--worker"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True)
    try:
        out, err = p.communicate(json.dumps(pedido), timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.communicate()
        raise RuntimeError(f"tempo esgotado ({timeout}s) — o transform foi interrompido")
    for linha in reversed(out.splitlines()):
        if linha.startswith(MARCA):
            return json.loads(linha[len(MARCA):])
    cauda = (err or "").strip()[-500:]
    raise RuntimeError(f"o worker terminou (código {p.returncode}) sem resultado" + (f": {cauda}" if cauda else ""))


def worker() -> int:
    """Lado do subprocesso. O stdout real fica reservado para a linha de resultado: qualquer
    print() do transform (ou de uma lib) vai para o stderr e não corrompe o protocolo."""
    saida_real = sys.stdout
    sys.stdout = sys.stderr
    try:
        pedido = json.loads(sys.stdin.read())
        nucleo = _nucleo()
        from transform.contexto import Contexto
        cfg = _registro().obter(pedido["id"])
        if cfg is None:
            raise RuntimeError("transform não encontrado no worker")
        r, do_cache = nucleo.Executor(_dir_cache()).executar(cfg, pedido["entrada"], lambda c: Contexto(c))
        resp = {"ok": True, "resultado": r.to_dict(), "do_cache": do_cache}
    except Exception as e:   # ErroTransform e qualquer defeito: mensagem legível para o analista
        resp = {"ok": False, "erro": f"{type(e).__name__}: {e}"}
    saida_real.write(MARCA + json.dumps(resp, ensure_ascii=False) + "\n")
    saida_real.flush()
    return 0


# --------------------------------------------------------------------------
# Catálogo
# --------------------------------------------------------------------------
FERRAMENTAS = [
    {"name": "listar_transforms",
     "description": ("Lista os transforms (estilo Maltego) disponíveis, opcionalmente só os que aceitam um tipo de "
                     "entidade. Mostra rota, se usa rede, se a chave de API existe no ~/.env (SIM/NÃO, nunca o "
                     "valor) e o motivo de indisponibilidade."),
     "inputSchema": {"type": "object", "properties": {
         "etype": {"type": "string", "enum": ["person", "organization", "other"]},
         "sub_etype": {"type": "string", "description": "subtipo de 'other' (ex.: dominio); exige etype"},
         "fonte": {"type": "string", "enum": ["base-propria", "api-aberta", "ia", "scraping"]}}},
     "handler": t_listar_transforms},
    {"name": "executar_transform",
     "description": ("Executa um transform sobre uma entidade e devolve a PROPOSTA (entidades e vínculos candidatos, "
                     "avisos, do_cache). Nunca grava em mapa, banco ou servidor — o analista aprova na GUI. "
                     "Roda em subprocesso com timeout; transform de IA pode demorar na fila do rolhama."),
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string", "description": "id do transform (ver listar_transforms)"},
         "text_label": {"type": "string", "description": "nome da entidade de entrada"},
         "etype": {"type": "string", "enum": ["person", "organization", "other"]},
         "sub_etype": {"type": "string"},
         "small_label": {"type": "string"},
         "description": {"type": "string"},
         "wikipedia": {"type": "string", "description": "URL http(s)"},
         "default_url": {"type": "string", "description": "URL http(s) do site oficial"},
         "urls": {"type": "array", "items": {"type": "string"}, "description": f"URLs de referência (máx. {MAX_URLS})"},
         "idioma": {"type": "string", "enum": list(IDIOMAS), "description": "padrão pt-BR"},
         "entity_id": {"type": "string", "description": "id da entidade no banco do CML, se já existir"},
         "timeout": {"type": "integer", "description": f"segundos; padrão {TIMEOUT_PADRAO}, máx. {TIMEOUT_MAXIMO}"}},
         "required": ["id", "text_label", "etype"]},
     "handler": t_executar_transform},
    {"name": "ver_log",
     "description": "Últimas execuções de transform (~/.cml_cache/transform.log): quando, qual, situação, tempo, rota e LLM.",
     "inputSchema": {"type": "object", "properties": {
         "n": {"type": "integer", "description": "quantas linhas; padrão 20, máx. 200"}}},
     "handler": t_ver_log},
    {"name": "limpar_cache",
     "description": ("Apaga o cache de resultados (só os .json dentro de ~/.cml_cache; o log fica). Com transform_id, "
                     "só o daquele transform. Recusa link simbólico e caminho fora do cache."),
     "inputSchema": {"type": "object", "properties": {"transform_id": {"type": "string"}}},
     "handler": t_limpar_cache},
    {"name": "backend_status",
     "description": ("Backend de LLM ativo (rolhama ou ollama), rota padrão e se CML_OLLAMA_URL, ROLHAMA_BDD_KEY e "
                     "CML_CRAUDIO_PORTA estão definidos. Só SIM/NÃO — nunca valores do ~/.env."),
     "inputSchema": {"type": "object", "properties": {}},
     "handler": t_backend_status},
]


# --------------------------------------------------------------------------
# JSON-RPC / MCP sobre stdio
# --------------------------------------------------------------------------
def responder(id_, resultado=None, erro=None) -> None:
    msg = {"jsonrpc": "2.0", "id": id_}
    if erro is not None:
        msg["error"] = erro
    else:
        msg["result"] = resultado
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def principal() -> int:
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            req = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if not isinstance(req, dict):
            continue

        metodo = req.get("method")
        id_ = req.get("id")

        if metodo == "initialize":
            versao = (req.get("params") or {}).get("protocolVersion") or "2025-06-18"
            responder(id_, {
                "protocolVersion": versao,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "cml-transforms", "version": "0.1.0"},
            })
        elif metodo in ("notifications/initialized", "initialized"):
            continue  # notificação: não se responde
        elif metodo == "ping":
            responder(id_, {})
        elif metodo == "tools/list":
            responder(id_, {"tools": [{k: f[k] for k in ("name", "description", "inputSchema")}
                                      for f in FERRAMENTAS]})
        elif metodo == "tools/call":
            params = req.get("params") or {}
            nome = params.get("name")
            args = params.get("arguments")
            if args is None:
                args = {}
            alvo = next((f for f in FERRAMENTAS if f["name"] == nome), None)
            if alvo is None:
                responder(id_, erro={"code": -32602, "message": f"ferramenta desconhecida: {nome}"})
                continue
            if not isinstance(args, dict):
                responder(id_, {"content": [{"type": "text", "text": "ERRO: 'arguments' deve ser um objeto"}],
                                "isError": True})
                continue
            try:
                texto = alvo["handler"](args)
                responder(id_, {"content": [{"type": "text", "text": texto}]})
            except Exception as e:  # erro de ferramenta, não do protocolo
                responder(id_, {"content": [{"type": "text", "text": f"ERRO: {e}"}], "isError": True})
        elif id_ is not None:
            responder(id_, erro={"code": -32601, "message": f"método não suportado: {metodo}"})
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        sys.exit(worker())
    sys.exit(principal())
