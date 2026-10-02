"""CNPJ pela BrasilAPI (dados abertos da Receita): quadro societario (QSA), atividade e sede.
O CNPJ tem de estar no nome, no apelido ou na descricao da entidade. CPF de socio vem
mascarado pela Receita e NAO e copiado. Data de entrada na sociedade vira start_date."""

import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( CURRENTDIR ) ) ) );

from transform.nucleo import Transform, Resultado, ErroTransform, ENTRADA;
from transform import _osint as o;

MAX_SOCIOS = 50;


class TransformCnpj(Transform):
    def executar(self, entrada, ctx):
        cnpj = o.exigir(o.cnpj_da_entrada(entrada), "um CNPJ válido", entrada);
        url = "https://brasilapi.com.br/api/cnpj/v1/" + cnpj;
        d = ctx.http().json(url);
        ref = ctx.ref("CNPJ %s (Receita Federal, via BrasilAPI)" % cnpj, url);
        r = Resultado();
        razao = o.titulo(d.get("razao_social"));
        r.aviso("Razão social: %s | situação: %s | abertura: %s" %
                (razao, d.get("descricao_situacao_cadastral", "?"), d.get("data_inicio_atividade", "?")));

        for i, s in enumerate((d.get("qsa") or [])[:MAX_SOCIOS]):
            nome = o.titulo(s.get("nome_socio"));
            if nome == "":
                continue;
            pj = s.get("identificador_de_socio") == 1;
            qual = str(s.get("qualificacao_socio") or "sócio").strip().lower();
            chave = "socio_%d" % i;
            desc = "Qualificação no quadro societário: %s." % qual;
            if pj:
                desc = "Pessoa jurídica sócia (CNPJ %s). " % s.get("cnpj_cpf_do_socio", "") + desc;
            r.entidade(chave, nome, etype="organization" if pj else "person", description=desc, referencias=[ref]);
            r.vinculo(chave, ENTRADA, "é " + qual + " de", start_date=o.data_iso(s.get("data_entrada_sociedade")), referencias=[ref]);

        cnae = d.get("cnae_fiscal");
        if cnae:
            nome = "CNAE %s – %s" % (cnae, o.corta(d.get("cnae_fiscal_descricao"), 120));
            r.entidade("cnae", nome, etype="other", sub_etype="atividade econômica",
                       description="Atividade econômica principal registrada na Receita.", referencias=[ref]);
            r.vinculo(ENTRADA, "cnae", "atua em", referencias=[ref]);
        if d.get("municipio"):
            nome = "%s/%s" % (o.titulo(d["municipio"]), d.get("uf", ""));
            r.entidade("sede", nome, etype="other", sub_etype="local",
                       description=o.corta("Município-sede no cadastro: %s %s, %s." %
                                           (o.titulo(d.get("descricao_tipo_de_logradouro", "")), o.titulo(d.get("logradouro", "")), d.get("bairro", "")), 300),
                       referencias=[ref]);
            r.vinculo(ENTRADA, "sede", "tem sede em", referencias=[ref]);
        return r;
