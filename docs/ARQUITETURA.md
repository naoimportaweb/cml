# CML — Arquitetura, fontes de dados e infraestrutura

Visão consolidada para humanos. O `CLAUDE.md` (raiz) é a referência **operacional** para agentes;
este documento é o panorama. Detalhes de deploy em `DEPLOY.md`; import de dados em
`docs/MISP-GALAXY.md`.

> **Regra de segredos (vale para todo `.md` versionado):** referencie a **variável**, nunca o
> **valor**. Host, senha, chave, caminho de produção — tudo vem do `~/.env` (fora do repo). Ver
> `DEPLOY.md` e a memória `env-credential-store`.

## Panorama em uma frase

CML é uma ferramenta de **análise de vínculos** (link analysis) para inteligência de ameaças:
um **cliente desktop PySide6** desenha mapas de relacionamento e organogramas, conversando com um
**servidor PHP + MySQL** por um envelope JSON-RPC próprio; um **terceiro tier de processamento
(o rolhama, na "máquina 90")** roda o LLM que gera relatórios e extrai entidades; e um **app web
somente-leitura** publica os mapas no navegador.

## As quatro peças

```
  ┌─────────────────┐   JSON-RPC        ┌──────────────────────┐
  │ Cliente desktop │  (envelope,       │ Servidor PHP + MySQL │
  │ PySide6 (app/)  │───criptografia────│ (server/)            │
  │                 │   RSA opcional)   │  domains multi-tenant│
  └────────┬────────┘                   └──────────┬───────────┘
           │ webapi (ChaCha20 por canal)           │  (mesmo MySQL)
           ▼                                        ▼
  ┌─────────────────────────┐            ┌──────────────────────┐
  │ rolhama — "máquina 90"  │            │ App web (PHP MVC)    │
  │ ollama + GPU (LLM)      │            │ server/webpage/      │
  │ report + extração       │            │ visualiza mapas      │
  └─────────────────────────┘            └──────────────────────┘
```

1. **Cliente desktop** (`app/`) — PySide6. Desenha os mapas (`view/ui/mapa_*_engine.py`), fala com
   o servidor via `ConnectObject.__execute__` (envelope JSON para `{server}/cml/services/execute.php`).
   Toda a lógica de report/extração roda **no cliente**, que orquestra o rolhama.
2. **Servidor** (`server/`) — PHP + MySQL, JSON-RPC com despacho dinâmico por `classe/versão`.
   Multi-tenant por **domain** (`data/config.json`). É o dono do banco (entidades, mapas,
   documentos, imagens). Detalhes no `CLAUDE.md` ("O envelope RPC", "Domains").
3. **rolhama (máquina 90)** — o tier de LLM. Ver seção própria abaixo.
4. **App web** (`server/webpage/`) — MVC PHP separado, **somente leitura**, para ver mapas e baixar
   documentos pelo navegador. Renderiza o mapa num canvas JS (inclui rostos/bandeiras e a aba
   "Relações"). Servido em `.../cml/webpage/`.

## Fluxo de dados (mapa → report)

1. O analista monta o mapa no cliente: entidades (`person`/`organization`/`other`/`link`),
   referências, subtipos, imagens/rosto. Salva → `MapRelationship.save` grava tudo no MySQL.
2. Ao gerar report, `report.py` **coleta as fontes** de cada entidade: os links da aba References
   **+ o site oficial (`default_url`) + a Wikipedia** da entidade (URLs http(s)), deduplicados.
3. Baixa o texto das fontes (até `MAX_REFERENCIAS`), monta **um único prompt** com a estrutura do
   mapa + os artigos, e manda ao **rolhama** (máquina 90) pelo canal do projeto.
4. O idioma do mapa (`language`) é **passado e reforçado** em toda chamada ao rolhama
   (`report.instrucao_idioma`, anexada como última linha do prompt).
5. A saída vira PDF (`QTextDocument`→`QPdfWriter`) e é anexada ao mapa como `Document`.

## O tier rolhama — a "máquina 90"

O **rolhama** é o serviço externo de LLM (repositório irmão `../rolhama/`, código do transporte em
`../rolhama/llm/`). No jargão do projeto é a **"máquina 90"** (aparece em comentários como o do
`report.py` sobre `ROLHAMA_OLLAMA_NUM_CTX`).

**Hardware (jul/2026):** GPU **RTX 5060, 16 GB** de VRAM.

**Modelo:** `qwen2.5:14b-instruct-q6_K` (default em `report.py`, sobrescrevível por
`CML_REPORT_MODELO`; usado pelo report **e** pelo bot de entidades). Encaixe na 16 GB: pesos q6_K
~12 GB + cache KV (16k de contexto) ~3 GB ≈ **~15 GB** — cabe, mas justo. Se der OOM: baixar
`ROLHAMA_OLLAMA_NUM_CTX` (12288/8192) no `~/.env` **da máquina 90** (o worker é quem manda no
`num_ctx`), ou voltar ao Q4 (`qwen2.5:14b-instruct`). O modelo precisa estar `ollama pull` no
servidor.

**Serialização global:** o worker do rolhama gera **uma coisa por vez em toda a máquina** — cada
chamada segura a fila de todos os projetos. Por isso o report manda **um prompt só** (não um por
referência) e o corte de referências existe para caber na janela de contexto (se estourar, o ollama
trunca em silêncio).

**Transporte (webapi):** o cliente fala o contrato **webapi** (`app/classlib/webapi.py` +
`bdd.py`, cópias literais de `../rolhama/llm/`). `enqueue`/`response` por **job UUID**, MAC de
autenticação, cifra **ChaCha20-Poly1305 por `(part, canal)`**. Sem rota de alocação de canal ainda,
então o canal é **fixo por projeto**: report (`"cml"`) → **507**, bot de entidades
(`"cml/entidades"`) → **508**. Variáveis: `ROLHAMA_WEBAPI_URL` (ou `ROLHAMA_BDD_URL`),
`ROLHAMA_BDD_KEY`, `ROLHAMA_OLLAMA_NUM_CTX`, `CML_REPORT_MODELO`, `CML_ROLHAMA_CANAL*`. Contrato
completo em `../rolhama/llm/INTEGRACAO.md` e `CANAIS.md`.

**A confirmar:** que os canais 507/508 estejam semeados e atendidos pelo worker na máquina 90.

## Fontes de dados externas

O CML consome dados de fora em três frentes:

| Fonte | O que traz | Como entra | Runtime? |
|---|---|---|---|
| **MISP Galaxy** (github.com/MISP/misp-galaxy) | Base de CTI: threat actors, malware, ransomware, RATs, tools, países, setores — com sinônimos, referências e relações | Importador offline (`script/misp_import.py`) lê os JSON e grava no MySQL. Ver `docs/MISP-GALAXY.md` | Não — import pontual |
| **flagcdn.com** | Bandeiras de países (PNG por código ISO) | Seed de países (rosto = bandeira) | Não — seed pontual |
| **rolhama / ollama** (máquina 90) | Geração de report e extração de entidades (LLM) | webapi por canal (ver acima) | **Sim** — em runtime |
| **Wikipedia / DuckDuckGo** | Busca de referências candidatas (bot `referencias`) e scrape (bot `wikipedia`) | Bots plug-in (`app/bot/brazil/`) | Sim — sob demanda |

O **MISP Galaxy** é o mais estruturante: ~7.900 entidades de CTI já importadas (threat-actor +
malware) mapeiam quase 1:1 no modelo do CML (value→entity, synonyms→`entity_aka`, refs→references,
tipo→`sub_etype`, related→`entity_simple_association`). Detalhes e como reexecutar/reverter em
`docs/MISP-GALAXY.md`. **Não é um banco que se "conecta"** — são arquivos JSON num repositório Git
que se baixa e importa.

## Onde ler cada coisa

- **Operacional para agentes / detalhes finos** → `CLAUDE.md`
- **Deploy em produção (Hostinger, flag-portão, `data/`, migrações)** → `DEPLOY.md`
- **Import do MISP Galaxy (mapeamento, reexecução, rollback)** → `docs/MISP-GALAXY.md`
- **Transporte rolhama / contrato webapi** → `../rolhama/llm/INTEGRACAO.md`, `CANAIS.md`
