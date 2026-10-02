# OSINT — fontes ligadas aos transforms do CML

Catálogo das fontes que viraram transform (`app/transform/api_aberta/<nome>/`). Contrato dos
transforms em `SPEC.md` §2; teste de integração em `app/transform/testes_osint.py`
(`python3 app/transform/testes_osint.py [trecho-do-id ...]`, usa a rede, sem Qt).
Levantamento e testes feitos em **2026-10-02**, com `curl`/`requests` e UA Firefox/157.

**Regras comuns:** toda saída leva referência (fonte + data de coleta *na descrição*, nunca em
`start_date`); datas que a fonte conhece (início de mandato, entrada na sociedade, 1ª captura,
data da matéria) viram `start_date` do vínculo e aparecem na timeline; tudo sai pela rota do
transform (`CML_TX_ROTA_PADRAO`, `direta` ou `tor`). Limites por execução estão no código de
cada transform (ex.: 150 subdomínios, 50 sócios, 40 URLs históricas).

## Transforms

"Entrada" é o que o transform lê da entidade: nome (`text_label`), apelido, URL oficial,
descrição, ou links (Wikipedia/referências). Para domínio/IP/ASN/CNPJ/CEP/e-mail **o valor tem
de estar no nome ou no apelido** da caixa (o CNPJ e o CEP também valem na descrição).

| Transform id | Fonte | Entrega | Chave | Limite da fonte | Entrada → saída |
|---|---|---|---|---|---|
| `wikidata.relacionados` | Wikidata | empregador, membro de, filiação, cargos, sede, país, subsidiárias, dirigentes; datas de início/fim viram `start_date`/`end_date` | não | gentil (UA identificável) | pessoa/org/outro (nome ou link da Wikipedia) → pessoa, org, outro:país/local/cargo |
| `crtsh.subdominios` | crt.sh (reserva: Cert Spotter) | subdomínios vistos em certificados TLS | não | crt.sh dá 502 intermitente → 3 tentativas e cai no Cert Spotter | domínio → outro:subdomínio |
| `dns.registros` | DoH Cloudflare (reserva Google) | A, AAAA, CNAME, MX, NS e `include:` do SPF | não | — | domínio → outro:ip, outro:domínio |
| `rdap.registro` | RDAP (via rdap.org) | registrador, servidores de nomes, data de registro; IP: bloco/rede e contato de abuso; ASN: nome | não | rdap.org redireciona ao registro certo; alguns limitam | domínio/IP/ASN → org, outro:domínio, outro:prefixo, outro:e-mail |
| `internetdb.exposicao` | Shodan InternetDB | portas abertas, hostnames, CVEs inferidas | não | sem limite documentado; só IP público (domínio é resolvido por DoH, até 3 IPs) | IP ou domínio → outro:porta, outro:domínio, outro:vulnerabilidade |
| `brasilapi.cnpj` | BrasilAPI (Receita) | quadro societário (data de entrada = `start_date`), CNAE, sede | não | gentil | org com CNPJ → pessoa, org, outro:atividade econômica, outro:local |
| `brasilapi.cep` | BrasilAPI v2 | logradouro, bairro, cidade, coordenadas | não | gentil | entidade com CEP → outro:local |
| `wayback.historico` | Wayback Machine (CDX) | 1ª e última captura; até 40 URLs HTML históricas (data da 1ª captura = `start_date`) | não | lento (≈15 s); CDX limita rajadas | domínio/URL → outro:arquivo web, outro:url |
| `abusech.urlhaus_threatfox` | URLhaus + ThreatFox | URLs de malware hospedadas e IOCs com família de malware | **`CML_TX_ABUSECH_KEY`** (grátis, auth.abuse.ch) | exigem `Auth-Key` desde 2025 (sem ela: 401, conferido) | domínio/IP → outro:url, outro:malware |
| `otx.reputacao` | AlienVault OTX | pulsos (campanhas) que citam o alvo, adversário e famílias de malware; com chave, DNS passivo | opcional `CML_TX_OTX_KEY` | anônimo só no `general`; `passive_dns` dá 429 sem chave | domínio/IP → outro:campanha de ameaça, org:ator de ameaça, outro:malware |
| `urlscan.varreduras` | urlscan.io | IPs, ASNs e URLs vistos em varreduras públicas (data da varredura = `start_date`) | opcional `CML_TX_URLSCAN_KEY` | busca anônima funciona; limite baixo | domínio/IP → outro:ip, outro:asn, outro:url |
| `github.perfil` | GitHub API | perfil, organizações, empresa, site, local, e-mail público; org → membros públicos; sem link, só candidatos por nome | opcional `CML_TX_GITHUB_KEY` (token sem escopo) | 60 req/h anônimo, 5000 com token | pessoa/org (link `github.com/<login>`) → outro:perfil, org, outro:domínio/local/e-mail |
| `gravatar.perfil` | Gravatar | titular, contas verificadas, sites e local do perfil público | não | gentil; **só o hash MD5 do e-mail sai da máquina** | e-mail → pessoa, outro:perfil |
| `ripestat.rede` | RIPEstat | IP: prefixo, ASN, contato de abuso; ASN: prefixos anunciados e vizinhos BGP | não | gentil | IP/ASN → outro:prefixo, outro:asn, outro:e-mail |
| `gdelt.noticias` | GDELT DOC 2.0 | matérias dos últimos 3 meses que citam o nome (data = `start_date`) | não | **1 consulta / 5 s por IP** (429 frequente; o transform espera e repete até 4×, ≈30 s) | nome (≥4 letras) → outro:matéria. Casa por texto: **homônimos entram** |
| `nominatim.lugar` | OpenStreetMap Nominatim | até 3 lugares, cidade e país da melhor correspondência, com coordenadas | não | política: 1 req/s, UA identificável (cache de 30 dias) | nome/endereço → outro:local, outro:país |
| `virustotal.relacoes` | VirusTotal v3 | veredito, resoluções DNS históricas, subdomínios | **`CML_TX_VIRUSTOTAL_KEY`** | grátis: 4 req/min, 500/dia | domínio/IP → outro:ip, outro:domínio, outro:subdomínio |
| `hunter.emails` | Hunter.io | e-mails públicos do domínio, nome e cargo quando conhecidos | **`CML_TX_HUNTER_KEY`** | grátis: 25 buscas/mês | domínio → outro:e-mail, pessoa |

### Subtipos de "Other" que os transforms preenchem

`domínio`, `subdomínio`, `ip`, `porta`, `vulnerabilidade`, `prefixo`, `asn`, `e-mail`, `url`,
`perfil`, `local`, `país`, `cargo`, `atividade econômica`, `arquivo web`, `malware`,
`campanha de ameaça`, `ator de ameaça`, `matéria`. O subtipo só vira dado do banco se já
estiver cadastrado em **File → Sub-tipos** (não há cadastro automático); sem isso a entidade
entra como *Other* comum. Cadastre os que for usar.

### Estado dos testes (2026-10-02, sem chave)

Rodados de ponta a ponta contra a rede: `wikidata`, `crtsh` (crt.sh deu 502 três vezes e o
**fallback Cert Spotter** respondeu), `dns`, `rdap`, `internetdb`, `brasilapi.cnpj` (Banco do
Brasil, 43 entidades), `brasilapi.cep`, `wayback`, `otx` (IP sem pulsos → aviso), `urlscan`,
`github` (torvalds), `gravatar`, `ripestat`, `gdelt` (passou após espera do 429), `nominatim`.
**Não testados com chave real:** `abusech.urlhaus_threatfox`, `virustotal.relacoes`,
`hunter.emails` — só o caminho "sem chave" (mensagem clara) foi exercitado; o formato de
resposta segue a documentação das APIs, então a 1ª execução com chave pode pedir ajuste.
`otx` com `CML_TX_OTX_KEY` (DNS passivo) e o ramo "organização" do `github` também não foram exercitados.

## Pesquisadas e NÃO implementadas

| Ferramenta | Motivo |
|---|---|
| BGPView (`api.bgpview.io`) | **Fora do ar** (sem resposta no teste). RIPEstat cobre o mesmo caso. |
| Shodan (API completa) | Paga; o InternetDB gratuito já está ligado. |
| Censys, SecurityTrails, FOFA, ZoomEye | Exigem chave com cadastro restrito/pago; baixo ganho sobre InternetDB + crt.sh + urlscan. |
| Have I Been Pwned (`breachedaccount`) | Chave paga (US$ 4,50/mês). Além disso, cruzar e-mail de pessoa física com vazamentos pede decisão do dono sobre escopo/LGPD. |
| HackerTarget (`hostsearch`) | Funciona, mas 50 consultas/dia por IP e entrega o que crt.sh + DNS já dão. |
| OpenCorporates | API exige chave desde 2023 e limita uso comercial; para CNPJ a BrasilAPI basta. |
| Portal da Transparência | Exige chave (`chave-api-dados`); **planejado** para o domain `corrupcao` (SPEC §5). |
| ipwho.is / ip-api (geolocalização de IP) | Funcionam; geolocalização de IP é imprecisa e induz erro em análise de vínculos. Fácil de somar depois. |
| X/Twitter, Facebook, Instagram, LinkedIn | API paga ou proibida pelos termos; coleta cairia em scraping (família `scraping`, via craudiowebot). |
| `subfinder`, `theHarvester`, `maigret`, `sherlock`, `amass`, `dig`, `whois` | **Nenhum está instalado nesta estação** (`which` vazio). Além disso, rodá-los foge do contrato (`ctx.http()` + `ctx.ref()`): exigiria `subprocess` com argumentos fixos e entrada validada por regex. `dig`/`whois` já estão cobertos por `dns.registros` (DoH, que respeita o Tor) e `rdap.registro`. Se o dono instalar algum, o lugar é `app/transform/ferramenta_local/<nome>/` (a `FONTES` do `nucleo.py` hoje não tem esse rótulo: usar `api-aberta` ou acrescentar `ferramenta-local`). |
