"""GitHub: se a entidade tem link github.com/<login> (URL oficial, Wikipedia ou referencias), traz
o perfil publico, organizacoes, empresa, site e local; sem link, procura candidatos pelo nome e
propoe so os perfis (nao assume que e a mesma pessoa). Sem chave: 60 req/h; CML_TX_GITHUB_KEY
(opcional, token sem escopo) sobe para 5000."""

import os, sys, inspect, re;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA, env;
from transform import _osint as o;

API = "https://api.github.com";
RE_LOGIN = re.compile(r"github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))(?:[/?#]|$)");
RESERVADOS = {"orgs", "users", "topics", "features", "about", "login", "settings", "marketplace", "sponsors", "enterprise"};
MAX_MEMBROS = 30;
MAX_CANDIDATOS = 5;


def _login(entrada):
    for u in [entrada.get("default_url"), entrada.get("wikipedia"), entrada.get("text_label")] + list(entrada.get("urls") or []):
        m = RE_LOGIN.search(str(u or ""));
        if m and m.group(1).lower() not in RESERVADOS:
            return m.group(1);
    return None;


class TransformGithub(Transform):
    def executar(self, entrada, ctx):
        chave = env("CML_TX_GITHUB_KEY");
        cab = {"Accept": "application/vnd.github+json"};
        if chave:
            cab["Authorization"] = "Bearer " + chave;
        http = ctx.http();
        r = Resultado();
        login = _login(entrada);

        if not login:
            nome = str(entrada.get("text_label") or "").strip();
            if len(nome) < 3:
                raise ErroTransform("sem link do GitHub e sem nome para procurar.");
            d = http.json(API + "/search/users", params={"q": nome + " in:fullname", "per_page": MAX_CANDIDATOS}, headers=cab);
            for u in d.get("items") or []:
                c = "gh_" + u["login"].lower();
                ref = ctx.ref("GitHub: " + u["login"], u["html_url"]);
                r.entidade(c, "GitHub: " + u["login"], etype="other", sub_etype="perfil",
                           description="Candidato por nome (não confirmado que seja a mesma pessoa/organização).", referencias=[ref]);
                r.vinculo(ENTRADA, c, "possível perfil", referencias=[ref]);
            if not r.entidades:
                r.aviso("Nenhum perfil do GitHub com esse nome.");
            else:
                r.aviso("Perfis encontrados só por nome — confirme antes de aceitar. Para o detalhe, ponha a URL github.com/<login> na entidade.");
            return r;

        p = http.json(API + "/users/" + login, headers=cab);
        ref = ctx.ref("GitHub: " + login, p["html_url"]);
        eh_org = p.get("type") == "Organization";
        r.entidade("perfil", "GitHub: " + login, etype="other", sub_etype="perfil",
                   description=o.corta("%s — %s repositórios públicos, %s seguidores. Conta criada em %s." %
                                       (p.get("name") or login, p.get("public_repos"), p.get("followers"), o.data_iso(p.get("created_at"))), 300),
                   referencias=[ref]);
        r.vinculo(ENTRADA, "perfil", "tem perfil", start_date=o.data_iso(p.get("created_at")), referencias=[ref]);
        if p.get("company"):
            emp = str(p["company"]).strip().lstrip("@");
            r.entidade("empresa", emp, etype="organization", description="Empresa declarada no perfil do GitHub de " + login + ".", referencias=[ref]);
            r.vinculo(ENTRADA, "empresa", "declara trabalhar em", referencias=[ref]);
        if p.get("blog"):
            host = o.host_de_texto(p["blog"]);
            if host:
                r.entidade("site", host, etype="other", sub_etype="domínio", description="Site declarado no perfil do GitHub de " + login + ".", referencias=[ref]);
                r.vinculo(ENTRADA, "site", "declara o site", referencias=[ref]);
        if p.get("location"):
            r.entidade("local", str(p["location"]).strip(), etype="other", sub_etype="local",
                       description="Localização declarada (texto livre) no perfil do GitHub.", referencias=[ref]);
            r.vinculo(ENTRADA, "local", "declara estar em", referencias=[ref]);
        if p.get("email"):
            r.entidade("email", p["email"].lower(), etype="other", sub_etype="e-mail", description="E-mail público no perfil do GitHub.", referencias=[ref]);
            r.vinculo(ENTRADA, "email", "usa o e-mail", referencias=[ref]);

        if eh_org:
            for m in http.json(API + "/orgs/%s/members" % login, params={"per_page": MAX_MEMBROS}, headers=cab):
                c = "gh_" + m["login"].lower();
                mref = ctx.ref("GitHub: " + m["login"], m["html_url"]);
                r.entidade(c, "GitHub: " + m["login"], etype="other", sub_etype="perfil", description="Membro público da organização " + login + " no GitHub.", referencias=[mref]);
                r.vinculo(c, "perfil", "é membro de", referencias=[mref]);
        else:
            for g in http.json(API + "/users/%s/orgs" % login, headers=cab)[:MAX_MEMBROS]:
                c = "org_" + g["login"].lower();
                gref = ctx.ref("GitHub: " + g["login"], "https://github.com/" + g["login"]);
                r.entidade(c, g["login"], etype="organization", description=o.corta(g.get("description") or "Organização no GitHub.", 200), referencias=[gref]);
                r.vinculo("perfil", c, "é membro de", referencias=[gref]);
        return r;
