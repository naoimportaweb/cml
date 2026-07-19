#!/usr/bin/env python3
"""Importa MISP Galaxy -> CML (MySQL). Ver docs/MISP-GALAXY.md.

Uso:
    # dry-run (padrao): so mostra o que entraria, NAO grava
    python3 script/misp_import.py --galaxies /caminho/misp-galaxy/clusters
    # gravar de fato
    python3 script/misp_import.py --galaxies /caminho/misp-galaxy/clusters --write
    # outro domain/projeto (default CYBERWARFARE): usa {PROJETO}_DB_* do ~/.env
    python3 script/misp_import.py --galaxies ... --project CYBERWARFARE --write

Credenciais do banco vêm do ~/.env (variável, nunca valor no repo — ver DEPLOY.md):
    {PROJETO}_DB_HOST_REMOTO, _USER, _PASSWORD, _DATABASE
Requer: pymysql. Idempotente (ON DUPLICATE KEY). UUID do MISP vira o id das entidades novas.
"""
import os, sys, json, hashlib, argparse

# (arquivo da galaxy, etype no CML, nome do sub_etype ou None). Edite para incluir mais.
GALAXIES = [
    ("threat-actor",  "organization", None),
    ("malpedia",      "other",        "malware"),
    ("ransomware",    "other",        "ransomware"),
    ("mitre-malware", "other",        "malware"),
    ("rat",           "other",        "rat"),
]
REFS_CAP = 8   # máximo de refs gravadas por entidade

def env_get(name):
    p = os.path.expanduser("~/.env")
    with open(p, errors="replace") as f:
        for ln in f:
            if ln.startswith(name + "="):
                return ln.split("=", 1)[1].rstrip("\n")
    return ""

def md5(s): return hashlib.md5(s.encode("utf-8")).hexdigest()
def bmp(s): return "".join(ch for ch in (s or "") if ord(ch) <= 0xFFFF)  # tira astral (col utf8)

def carregar(base, nome):
    p = os.path.join(base, nome + ".json")
    if not os.path.exists(p):
        print("  (aviso: galaxy não encontrada: %s)" % p); return []
    return json.load(open(p, encoding="utf-8")).get("values") or []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--galaxies", required=True, help="diretório clusters/ do clone do misp-galaxy")
    ap.add_argument("--project", default="CYBERWARFARE", help="prefixo das vars {PROJETO}_DB_* no ~/.env")
    ap.add_argument("--write", action="store_true", help="gravar (default é dry-run)")
    args = ap.parse_args()

    import pymysql
    P = args.project
    con = pymysql.connect(host=env_get(P+"_DB_HOST_REMOTO"), user=env_get(P+"_DB_USER"),
                          password=env_get(P+"_DB_PASSWORD"), database=env_get(P+"_DB_DATABASE"),
                          charset="utf8mb4", connect_timeout=30, autocommit=False)
    cur = con.cursor()
    cur.execute("SELECT id FROM entity"); ids_db = set(r[0] for r in cur.fetchall())
    cur.execute("SELECT id, LOWER(text_label) FROM entity")
    nome_para_id = {}
    for eid, ln in cur.fetchall(): nome_para_id.setdefault(ln, eid)
    print("banco antes: %d entidades" % len(ids_db))

    valores = []
    for arq, etype, sub in GALAXIES:
        for v in carregar(args.galaxies, arq):
            if v.get("revoked"): continue
            uuid = v.get("uuid"); nome = bmp((v.get("value") or "").strip())
            if uuid and nome: valores.append((v, etype, sub, uuid, nome))

    ent = {}; subs = {}; aka = {}; refs = {}; assoc = {}; uuid2id = {}
    novos = enriq = 0
    for v, etype, sub, uuid, nome in valores:
        ln = nome.lower()
        if uuid in ids_db:
            cid = uuid
        elif ln in nome_para_id:
            cid = nome_para_id[ln]; enriq += 1
        else:
            cid = uuid; nome_para_id[ln] = uuid; novos += 1
            subid = None
            if sub: subid = md5(sub); subs[subid] = sub
            ent[uuid] = (uuid, nome, etype, subid, bmp(v.get("description") or ""))
        uuid2id[uuid] = cid
        meta = v.get("meta") or {}
        for syn in (meta.get("synonyms") or []):
            s = bmp(str(syn).strip())[:255]
            if s: aka[md5(cid+"|"+s)] = (md5(cid+"|"+s), cid, s)
        for url in (meta.get("refs") or [])[:REFS_CAP]:
            u = str(url).strip()
            if u: refs[md5(cid+"|"+u)] = (md5(cid+"|"+u), cid, u[:255], u)
    for v, etype, sub, uuid, nome in valores:
        frm = uuid2id.get(uuid)
        for r in (v.get("related") or []):
            to = uuid2id.get(r.get("dest-uuid"))
            if frm and to and frm != to: assoc[md5(frm+"|"+to)] = (md5(frm+"|"+to), frm, to)

    print("plano: %d novas, %d enriquecidas(nome), %d sub_etypes, %d aka, %d refs, %d relações"
          % (novos, enriq, len(subs), len(aka), len(refs), len(assoc)))

    if not args.write:
        con.close()
        print("\n*** DRY-RUN — nada gravado. Rode com --write para gravar. ***")
        return

    def multi(head, tpl, suf, rows, nparams, batch=300):
        rows = list(rows)
        for i in range(0, len(rows), batch):
            chunk = rows[i:i+batch]
            flat = []
            for r in chunk: flat.extend(r[:nparams])
            cur.execute(head + ",".join([tpl]*len(chunk)) + suf, flat)

    try:
        multi("INSERT INTO sub_etype (id,name) VALUES", "(%s,%s)", " ON DUPLICATE KEY UPDATE name=name",
              [(k, v) for k, v in subs.items()], 2, 1000)
        multi("INSERT INTO entity (id,text_label,etype,sub_etype_id,description) VALUES",
              "(%s,%s,%s,%s,%s)", " ON DUPLICATE KEY UPDATE id=id", ent.values(), 5, 300)
        multi("INSERT INTO entity_aka (id,entity_id,name) VALUES", "(%s,%s,%s)",
              " ON DUPLICATE KEY UPDATE name=name", aka.values(), 3, 1000)
        multi("INSERT INTO diagram_relationship_element_reference (id,entity_id,title,link1,link2,link3,description,about,date_news) VALUES",
              "(%s,%s,%s,%s,'','','','','2000-01-01')", " ON DUPLICATE KEY UPDATE link1=VALUES(link1)",
              refs.values(), 4, 500)
        multi("INSERT INTO entity_simple_association (id,entity_from_id,entity_to_id) VALUES",
              "(%s,%s,%s)", " ON DUPLICATE KEY UPDATE id=id", assoc.values(), 3, 1000)
        con.commit()
        cur.execute("SELECT COUNT(*) FROM entity")
        print("OK — commit feito. banco agora: %d entidades." % cur.fetchone()[0])
    except Exception as e:
        con.rollback(); print("ROLLBACK — erro:", e); raise
    finally:
        con.close()

if __name__ == "__main__":
    main()
