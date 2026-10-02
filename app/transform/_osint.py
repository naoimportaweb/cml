"""Ajudantes compartilhados pelos transforms de OSINT (api_aberta/*): extrair o alvo da
entidade de entrada (dominio, IP, ASN, CNPJ, CEP, e-mail), repetir requisicao que falha por
instabilidade da fonte e normalizar texto. Sem Qt e sem rede propria — a rede e sempre do
ctx.http()."""

import re, ipaddress, time, hashlib;
from urllib.parse import urlparse;

from transform.nucleo import ErroTransform, norm;

RE_DOMINIO = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$");
RE_ASN     = re.compile(r"^(?:AS)?\s*(\d{1,10})$", re.I);
RE_EMAIL   = re.compile(r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,63}");
RE_CEP     = re.compile(r"(?<!\d)(\d{5})-?(\d{3})(?!\d)");
RE_CNPJ    = re.compile(r"(?<!\d)(\d{2})\.?(\d{3})\.?(\d{3})/?(\d{4})-?(\d{2})(?!\d)");
SUFIXOS_ESTATICOS = (".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".map", ".mp4", ".webp");


def corta(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip();
    return s if len(s) <= n else s[:n - 1].rstrip() + "…";


def _candidatos(entrada):
    # Onde o analista pode ter escrito o alvo: nome, apelido, URL oficial. Nessa ordem.
    for k in ("text_label", "small_label", "default_url"):
        v = str(entrada.get(k) or "").strip();
        if v != "":
            yield v;


def host_de_texto(v):
    v = str(v or "").strip();
    if v == "":
        return None;
    p = urlparse(v if "://" in v else "//" + v);
    h = (p.hostname or "").strip(".").lower();
    try:
        h = h.encode("idna").decode("ascii");
    except Exception:
        pass;
    return h if RE_DOMINIO.match(h) else None;


def dominio_da_entrada(entrada):
    for v in _candidatos(entrada):
        h = host_de_texto(v);
        if h:
            return h;
    return None;


def ip_de_texto(v):
    v = str(v or "").strip().strip("[]");
    try:
        return str(ipaddress.ip_address(v));
    except Exception:
        return None;


def ip_da_entrada(entrada):
    for v in _candidatos(entrada):
        ip = ip_de_texto(v) or ip_de_texto(urlparse(v if "://" in v else "//" + v).hostname);
        if ip:
            return ip;
    return None;


def ip_publico(ip):
    try:
        a = ipaddress.ip_address(ip);
        return not (a.is_private or a.is_loopback or a.is_link_local or a.is_multicast or a.is_reserved or a.is_unspecified);
    except Exception:
        return False;


def asn_da_entrada(entrada):
    for v in _candidatos(entrada):
        m = RE_ASN.match(v.strip());
        if m:
            return int(m.group(1));
    return None;


def cnpj_valido(d):
    if len(d) != 14 or d == d[0] * 14:
        return False;
    def dv(base):
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(base):];
        r = sum(int(c) * p for c, p in zip(base, pesos)) % 11;
        return "0" if r < 2 else str(11 - r);
    return d[12] == dv(d[:12]) and d[13] == dv(d[:13]);


def cnpj_da_entrada(entrada):
    for k in ("text_label", "small_label", "description"):
        for m in RE_CNPJ.finditer(str(entrada.get(k) or "")):
            d = "".join(m.groups());
            if cnpj_valido(d):
                return d;
    return None;


def cep_da_entrada(entrada):
    for k in ("text_label", "small_label", "description"):
        m = RE_CEP.search(str(entrada.get(k) or ""));
        if m:
            return m.group(1) + m.group(2);
    return None;


def email_da_entrada(entrada):
    for k in ("text_label", "small_label", "description"):
        m = RE_EMAIL.search(str(entrada.get(k) or ""));
        if m:
            return m.group(0).lower();
    return None;


def exigir(valor, o_que, entrada):
    if not valor:
        raise ErroTransform("a entidade '%s' não parece ser %s (ponha o valor no nome, no apelido ou na URL oficial)." %
                            (corta(entrada.get("text_label"), 60), o_que));
    return valor;


def com_tentativas(fn, tentativas=3, pausa=2.0):
    """Repete `fn` quando a fonte esta instavel (crt.sh devolve 502 de tempos em tempos)."""
    ultimo = None;
    for i in range(tentativas):
        try:
            return fn();
        except ErroTransform as e:
            ultimo = e;
            if "cancelado" in str(e):
                raise;
            if i < tentativas - 1:
                time.sleep(pausa * (i + 1));
    raise ultimo;


def titulo(nome):
    # CAIXA ALTA do cadastro vira Nome Proprio, sem maiusculizar "de/da/do/e".
    miudas = {"de", "da", "do", "das", "dos", "e", "di", "du"};
    palavras = str(nome or "").strip().lower().split();
    return " ".join(p if (i > 0 and p in miudas) else p.capitalize() for i, p in enumerate(palavras));


def data_iso(v):
    """'+2019-03-04T00:00:00Z', '2019-03-04T10:00', '20190304120000' -> '2019-03-04' (ou None)."""
    v = str(v or "").strip().lstrip("+");
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", v) or re.match(r"^(\d{4})(\d{2})(\d{2})", v);
    if not m:
        return None;
    a, mes, d = m.groups();
    if a == "0000":
        return None;
    return "%s-%s-%s" % (a, "01" if mes == "00" else mes, "01" if d == "00" else d);


def md5_hex(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest();


def nome_chave(prefixo, valor):
    return prefixo + "_" + re.sub(r"[^a-z0-9]+", "_", norm(valor))[:60];
