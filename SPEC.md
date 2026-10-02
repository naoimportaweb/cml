# SPEC — CML rumo ao nível do Maltego

> **Status (2026-10-02): Fase 1 implementada, ainda não validada na GUI real nem em produção.**
> Ver **§7 Estado e próximos passos**. Decisões do dono em **Decisões**.

Referência: o Maltego. O carro-chefe do CML continua sendo o **mapa conceitual** (análise de
vínculos com curadoria humana, datas, referências, organograma, timeline). O que falta para
ficar no patamar do Maltego não é desenhar melhor — é **descobrir dados a partir de uma
entidade**. Este SPEC trata primeiro disso (Fase 1: **Transforms**) e lista o resto em fases.

## Decisões (do dono, 2026-10-02)

1. **Prioridade:** Transforms primeiro; o roadmap completo vem em fases.
2. **Fontes de dados** — as quatro: (a) bancos próprios (MISP, países, `entity_simple_association`);
   (b) APIs abertas; (c) extração por IA via `rolhama`; (d) scraping via `craudiowebot`.
3. **Onde rodam:** **no cliente PySide6**, estendendo o modelo de plug-ins de `app/bot/`.

Consequências da decisão 3 (a registrar, não a contestar):
- Chaves de API ficam no `~/.env` **de cada estação** (`CML_TX_<FONTE>_KEY`); nunca em
  `config.json` de transform nem em arquivo versionado.
- Não há cache nem auditoria centralizados de graça. Por isso o cache e o log de execução
  (§2.5) ficam no cliente, e o **resultado** é que vai ao servidor, pelo caminho normal de
  salvar mapa.
- A **lei do workspace** vale: todo LLM passa pelo `rolhama` (canal próprio, E2E); todo curl
  externo usa User-Agent do Firefox corrente.

## 1. Lacuna em relação ao Maltego

| Capacidade do Maltego | CML hoje | Fase |
|---|---|---|
| Transform: entidade → consulta → novas entidades/vínculos | só bots-botão em diálogo (`app/bot/`), sem ligar resultado ao mapa | **1** |
| Menu de contexto por tipo de entidade | inexistente | **1** |
| Machines (encadear transforms) | inexistente | 2 |
| Layouts automáticos (orgânico, hierárquico, circular, bloco) | posição manual | 2 |
| Peso de vínculo, tamanho por centralidade, filtros, busca no canvas | parcial (só tipo/rosto) | 2 |
| Seleção em massa e ação sobre seleção | inexistente | 2 |
| Importar/exportar (CSV, GraphML, STIX 2.1) | só `DialogImport` (1 JSON por entidade) | 3 |
| Colaboração em tempo real | trava consultiva por mapa | 3 |
| Hub/loja de transforms | — | fora de escopo |

Já temos e o Maltego **não** tem (preservar): datas e períodos em tudo, referência com fonte
datada, timeline com 6 origens, organograma, report PDF por IA, federação entre servidores,
regras editoriais (`EDITORIAL.md`).

## 2. Fase 1 — Transforms

### 2.1 Conceito

Um **transform** é uma função `(entidade de entrada) → lista de entidades + vínculos`.
O analista dá botão direito numa caixa do mapa, escolhe o transform da lista filtrada pelo
`etype`/`sub_etype` da caixa, e o resultado aparece **como proposta** (§2.4) — nunca grava
direto no mapa.

### 2.2 Contrato do plug-in

Reaproveita o desenho de `app/bot/<pais>/<nome>/` (um `config.json` + um módulo carregado por
`importlib` no clique), mas **sem diálogo obrigatório**. Local novo: `app/transform/<fonte>/<nome>/`.

`config.json`:
```json
{
  "id": "dns.resolve",
  "nome": "Resolver DNS",
  "versao": "1",
  "entrada": ["other:dominio"],
  "saida": ["other:ip"],
  "fonte": "api-aberta",
  "rede": true,
  "rota": "direta",
  "chave_env": null,
  "path": "transform/dns/resolve.py",
  "class": "TransformDnsResolve"
}
```
- `entrada`: lista de `etype` ou `etype:sub_etype` aceitos (filtra o menu).
- `fonte`: `base-propria` | `api-aberta` | `ia` | `scraping` — só rótulo e agrupamento no menu.
- `rota`: `direta` | `tor` | ausente (usa `CML_TX_ROTA_PADRAO`); ver §5.
- `rede`/`chave_env`: para o menu avisar *antes* de executar que vai sair da máquina e que a
  chave falta.

Módulo: classe com `executar(entrada: dict, ctx) -> Resultado`, sem Qt, para ser testável com
`python3` direto (padrão do `fussador`: núcleo × casca). `ctx` entrega `ctx.http()` (curl/requests
com UA do Firefox corrente), `ctx.llm()`, `ctx.craudio()`, `ctx.cache`, `ctx.log`.

`Resultado` (estrutura única, serializável):
```json
{
  "entidades": [{"chave": "e1", "text_label": "...", "etype": "other",
                 "sub_etype": "ip", "small_label": "", "description": "",
                 "referencias": [{"title": "...", "link1": "https://...", "start_date": null}]}],
  "vinculos":  [{"de": "ENTRADA", "para": "e1", "verbo": "resolve para",
                 "start_date": null, "end_date": null}],
  "avisos":    []
}
```
`"ENTRADA"` é a caixa de onde o transform partiu; `chave` é local ao resultado.
**Toda informação gerada carrega referência** (URL da fonte + data de coleta) — é o que mantém o
princípio editorial "fonte só na referência".

### 2.3 Famílias de transform (fontes)

1. **Base própria** — consulta `Entity.search` e `entity_simple_association` (relações globais do MISP, ainda sem UI).
   Offline em relação ao mundo, sem vazar a consulta. É o primeiro a implementar: prova o contrato sem rede externa.
2. **APIs abertas** — DNS/whois/crt.sh, Wikipedia/Wikidata, Wayback, bases de transparência.
   Uma por vez; cada uma declara `chave_env` quando precisa.
3. **IA (`rolhama`)** — generaliza o bot `entidades` (texto/URL → JSON de entidades e vínculos)
   como transform. Herda: um prompt só por execução (worker serializa globalmente), idioma do
   mapa reforçado no output, canal próprio (**a alocar** — ver §5), e o aviso de que a `.90`
   pode estar desligada (a fila espera alguém ligá-la; o transform deve mostrar "na fila", não travar a GUI).
   **2.3.1 Backend de LLM selecionável.** O transform não chama o `rolhama` nem o Ollama: chama
   `ctx.llm()`, que escolhe o backend por `CML_LLM_BACKEND` no `~/.env` (e por `"llm"` no
   `config.json`, quando o transform exigir um):
   - `rolhama` (**padrão**): canal 510, E2E, fila global, `.90` pode estar desligada.
   - `ollama`: HTTP direto no endpoint de `CML_OLLAMA_URL` (sem padrão embutido; sem a variável,
     o backend não liga). Mesma interface (`gerar(prompt, model, formato, idioma_instrucao)`),
     então o transform não muda.
   - ⚠️ **Exceção à lei do workspace** ("todo acesso a LLM passa pelo rolhama"): o Ollama direto
     perde o E2E e a serialização global da fila. Por isso é **opt-in** (nunca o padrão), o
     menu mostra o backend ativo antes de executar e a execução entra no log local (§2.5).
     Se o dono quiser torná-la regra, atualizar a lei no `workspace/CLAUDE.md` — **este SPEC não
     a altera**.
4. **Scraping (`craudiowebot`)** — job JSON pelo contrato do `craudiowebot/SPEC.md` (modo
   `--servir`, socket TCP) para fontes sem API. Mudança de comportamento no craudiowebot exige
   atualizar o SPEC dele.

### 2.4 Fluxo de resultado: proposta, não gravação

Curadoria humana é o diferencial do CML; transform automático despeja lixo se gravar direto.
- O resultado abre um painel **Proposta**: lista com caixa de seleção por entidade e por vínculo,
  origem/fonte visível, e **marcação de duplicata**.
- **Buscar antes de criar:** para cada entidade proposta, o cliente chama `Entity.search`; se achar,
  oferece *reaproveitar o id existente* (padrão) ou *criar nova*. Entidades são globais.
- Aceitar = inserir as caixas/vínculos no mapa aberto. Persistência só no **save do mapa**
  (mesmo comportamento do `incorporate`); a trava consultiva do mapa vale — mapa travado não aceita.
- Entidade criada por transform recebe `id` nativo (`hex_hex_hex`), nunca UUID (reservado ao MISP).

### 2.5 Execução, cache e log

- Roda em `QThread` próprio (mesmo princípio do `ReportManager`: a thread não pertence ao
  diálogo). Cancelável; timeout por transform.
- Cache local em `~/.cml_cache/` por `(transform_id, versao, hash(entrada))` com TTL declarado no
  `config.json`. Evita repetir consulta externa e queimar cota de API.
- Log de execução local (quando, qual transform, qual entrada, quantas entidades) — é a única
  trilha de auditoria que a decisão 3 permite; não vai ao servidor.

### 2.6 UI

- Botão direito numa caixa/vínculo do `mapa_relationship_engine.py`: submenu **Transforms**,
  agrupado por `fonte`, desabilitado com motivo (falta chave, mapa travado).
- Painel **Proposta** (§2.4) e indicador de execuções em andamento (como o botão "Documents").
- Transform em lote sobre **seleção** depende da seleção em massa (Fase 2); na Fase 1 é uma
  caixa por vez.

### 2.7 Entregáveis da Fase 1 (ordem)

1. Contrato + carregador + `Resultado` + painel Proposta, com 1 transform de **base própria**.
2. Menu de contexto filtrado por tipo.
3. Cache + log + cancelamento.
4. Transform `ia` (generalização do bot `entidades`).
5. Transforms de API aberta, nesta ordem: Wikidata, crt.sh, DNS (§5).
6. Transform `scraping` de ponta a ponta com o `craudiowebot`.

## 3. Fase 2 — Análise visual (esboço)

Layouts automáticos (orgânico/force-directed, hierárquico, circular, bloco) como **ação**, não
modo permanente — o analista mantém posição manual depois. Peso de vínculo (campo novo no
`diagram_relationship_link`) e tamanho por grau/centralidade. Filtro e busca no canvas.
Seleção em massa (base para transform em lote). **Machines**: sequência de transforms em JSON,
com profundidade e limite de entidades por passo (sem limite, uma machine explode o mapa).

## 4. Fase 3 — Dados e colaboração (esboço)

Exportar/importar CSV, GraphML e STIX 2.1 (casa com a origem MISP). Substituir a trava
consultiva por edição colaborativa — decisão grande, exige estudo próprio (o servidor é
JSON-RPC sem canal de push). Histórico navegável (`diagram_relationship_history` já acumula).

## 5. Decisões da segunda rodada e questões abertas

**Resolvidas (2026-10-02):**
- **APIs abertas (carta branca ao Claude):** ordem de implementação — (1) **Wikidata** (sem chave,
  casa com o campo `wikipedia` da entidade), (2) **crt.sh** (subdomínios por certificado, sem chave),
  (3) **DNS** (resolução direta). Portal da Transparência entra quando o domain `corrupcao`
  pedir, pois exige chave (`CML_TX_TRANSPARENCIA_KEY`).
- **Rede no Qubes:** o transform **declara** o caminho no `config.json` — campo `"rota"`:
  `"direta"` (qube de rede, ex. `sys-firewall`) ou `"tor"` (`sys-whonix`) — e o cliente usa o
  proxy correspondente. Quem decide o padrão é a rede da estação (`CML_TX_ROTA_PADRAO` no `~/.env`);
  o `config.json` do transform só fixa a rota quando a fonte exige (ex.: consulta sensível
  → sempre `"tor"`). Transform `rede: true` sem rota resolvível não executa e diz por quê.
- **`webapi.py`:** recopiado byte a byte de `../rolhama/llm/webapi.py` (voltou a ter `recuperar()`).

**Adiada:** campo de **confiança** (0–100) por vínculo gerado — decidir depois da Fase 1; o
painel de proposta ordena por fonte e por duplicata até lá.

**Resolvida (3ª rodada):** o transform de IA usa o canal **510** do `rolhama`, o mesmo do bot
`entidades`. O dono também pediu a possibilidade de falar com o **Ollama diretamente** — ver §2.3.1.

## 6. Fora de escopo

Hub/loja de transforms de terceiros; execução de transform no servidor (descartada na decisão 3);
qualquer coleta que contorne autenticação ou termos de uso de uma fonte.

## 7. Estado e próximos passos (retomada em 2026-10-04)

**Feito (2026-10-02):** núcleo sem Qt (`app/transform/`), menu de contexto, painel Proposta,
aplicar em círculo com dedup, gerente em thread, cache/log locais, backend LLM rolhama(510)/ollama,
transforms `base.parecidas`, `base.associadas`, `ia.extrair`, `scraping.links_externos`, conectores
OSINT em `app/transform/api_aberta/` (ver `docs/OSINT.md`), servidor MCP `cml-transforms`
(`docs/MCP.md`), `Entity.associations` no PHP. Testes só headless/offscreen.

**Falta, em ordem:**
1. **Rodar o app de verdade** (`python3 app/application.py`, servidor real): botão direito → transform
   → Proposta → aplicar → salvar. Nada disso foi visto na tela.
2. **Deploy do servidor** (flag-portão do `DEPLOY.md`) para `Entity.associations`; testar `base.associadas`.
3. Testar com serviços reais: `ia.extrair` (rolhama 510 — confirmar canal semeado e `.90` ligada) e
   `scraping.links_externos` (`browser.py --servir`).
4. Rodar `app/transform/testes_osint.py` e conferir quais conectores passam; chaves faltantes
   (`CML_TX_<FONTE>_KEY`) no `~/.env`.
5. MCP: login no servidor do CML sem Qt, para os transforms de base funcionarem por ele.
6. Fase 2 (layouts, peso de vínculo, filtros, seleção em massa, machines) e Fase 3 (§3, §4).
7. Decidir se o Ollama direto vira regra no `workspace/CLAUDE.md` (hoje é exceção opt-in).
