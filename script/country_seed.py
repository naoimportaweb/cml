#!/usr/bin/env python3
"""Seed de países com a BANDEIRA como rosto (entity_face). Fonte dos nomes/códigos ISO: a
galaxy `country` do MISP; bandeira: flagcdn (PNG). etype 'other'; id = uuid5 do ISO (formato
UUID, reversível como o import MISP). Enriquece por nome (país já existente ganha a bandeira,
sem duplicar). Idempotente. Ver docs/MISP-GALAXY.md.

Uso:
    python3 script/country_seed.py --country /caminho/misp-galaxy/clusters/country.json           # dry-run
    python3 script/country_seed.py --country .../country.json --write                             # grava
Credenciais do banco do ~/.env ({PROJETO}_DB_HOST_REMOTO/_USER/_PASSWORD/_DATABASE).
Requer: pymysql, requests.
"""
import os, sys, json, uuid, base64, argparse

def env_get(name):
    with open(os.path.expanduser("~/.env"), errors="replace") as f:
        for ln in f:
            if ln.startswith(name + "="): return ln.split("=", 1)[1].rstrip("\n")
    return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", required=True, help="clusters/country.json do clone do misp-galaxy")
    ap.add_argument("--project", default="CYBERWARFARE")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--size", default="w320", help="tamanho do flagcdn (w320, w160, ...)")
    args = ap.parse_args()
    import pymysql, requests

    NS = uuid.uuid5(uuid.NAMESPACE_DNS, "cml-country")
    vals = json.load(open(args.country, encoding="utf-8")).get("values") or []
    paises = []
    for v in vals:
        iso = ((v.get("meta") or {}).get("ISO") or "").strip().lower()
        nome = (v.get("description") or v.get("value") or "").strip()
        if iso and nome: paises.append((str(uuid.uuid5(NS, iso)), nome, iso))
    print("países no galaxy:", len(paises))

    s = requests.Session(); s.headers["User-Agent"] = "CML-seed/1.0"
    flags = {}; falhas = 0
    for i, (cid, nome, iso) in enumerate(paises):
        try:
            r = s.get("https://flagcdn.com/%s/%s.png" % (args.size, iso), timeout=12)
            if r.status_code == 200 and r.content[:8] == b"\x89PNG\r\n\x1a\n":
                flags[cid] = base64.b64encode(r.content).decode("ascii")
            else: falhas += 1
        except Exception: falhas += 1
        if (i+1) % 50 == 0: print("  ...%d/%d" % (i+1, len(paises)))
    print("bandeiras: %d (falhas %d)" % (len(flags), falhas))

    P = args.project
    con = pymysql.connect(host=env_get(P+"_DB_HOST_REMOTO"), user=env_get(P+"_DB_USER"),
                          password=env_get(P+"_DB_PASSWORD"), database=env_get(P+"_DB_DATABASE"),
                          charset="utf8mb4", connect_timeout=30, autocommit=False)
    c = con.cursor()
    c.execute("SELECT id, LOWER(text_label) FROM entity")
    nome_para_id = {}
    for eid, ln in c.fetchall(): nome_para_id.setdefault(ln, eid)

    ent = []; faces = []; novos = enriq = 0
    for cid, nome, iso in paises:
        if cid not in flags: continue
        ln = nome.lower()
        if ln in nome_para_id: alvo = nome_para_id[ln]; enriq += 1
        else: alvo = cid; ent.append((cid, nome, "other", nome)); novos += 1
        faces.append((alvo, flags[cid]))
    print("plano: %d novos, %d enriquecidos, %d bandeiras" % (novos, enriq, len(faces)))
    if not args.write:
        con.close(); print("\n*** DRY-RUN — nada gravado (use --write). ***"); return

    def multi(head, tpl, suf, rows, n, batch=100):
        rows = list(rows)
        for i in range(0, len(rows), batch):
            ch = rows[i:i+batch]; flat = []
            for r in ch: flat.extend(r[:n])
            c.execute(head + ",".join([tpl]*len(ch)) + suf, flat)
    try:
        multi("INSERT INTO entity (id,text_label,etype,description) VALUES", "(%s,%s,%s,%s)",
              " ON DUPLICATE KEY UPDATE id=id", ent, 4, 300)
        multi("INSERT INTO entity_face (entity_id,png_base64) VALUES", "(%s,%s)",
              " ON DUPLICATE KEY UPDATE png_base64=VALUES(png_base64)", faces, 2, 100)
        con.commit()
        c.execute("SELECT COUNT(*) FROM entity_face")
        print("OK — commit. entity_face agora: %d" % c.fetchone()[0])
    except Exception as e:
        con.rollback(); print("ROLLBACK:", e); raise
    finally:
        con.close()

if __name__ == "__main__":
    main()
