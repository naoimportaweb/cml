# SPEC — CML melhor que Maltego, Obsidian e Siren

> **Status (2026-10-05):** Fase 1 (Transforms) implementada, **ainda não validada na GUI real nem
> em produção**. Referências ampliadas de um para três sistemas. **O `rolhama` caiu e não volta
> (custava manter ligado): a lei do workspace virou "LLM é local e sob demanda" e o substituto
> está em §8** — Ollama local pelo app, OpenCode/MCP para trabalho conduzido. Nada de IA no
> caminho crítico.
> Estado e fila em **§9**. Decisões do dono em **Decisões**.

O carro-chefe do CML continua sendo o **mapa conceitual**: análise de vínculos com curadoria
humana, datas, referências, organograma e timeline. Este SPEC diz o que falta para passar à
frente dos três sistemas que o dono elegeu como régua — e **não** é "ter mais recursos que eles".
É explorar três eixos que os três deixam de fora (§1.3).

## Decisões (do dono)

**2026-10-02**

1. **Prioridade:** Transforms primeiro; o roadmap completo vem em fases.
2. **Fontes de dados** — as quatro: (a) bancos próprios (MISP, países, `entity_simple_association`);
   (b) APIs abertas; (c) extração por IA; (d) scraping via `craudiowebot`.
3. **Onde rodam:** **no cliente PySide6**, estendendo o modelo de plug-ins de `app/bot/`.

Consequências da decisão 3 (a registrar, não a contestar):
- Chaves de API ficam no `~/.env` **de cada estação** (`CML_TX_<FONTE>_KEY`); nunca em
  `config.json` de transform nem em arquivo versionado.
- Não há cache nem auditoria centralizados de graça. Por isso o cache e o log de execução
  (§2.5) ficam no cliente, e o **resultado** é que vai ao servidor, pelo caminho normal de
  salvar mapa.
- Todo curl externo usa User-Agent do Firefox corrente.

**2026-10-05**

4. **Três réguas, não uma:** **Maltego** (descoberta), **Obsidian** (grafo que nasce da escrita)
   e **Siren** (investigação sobre dados em escala). Em relação aos três, a meta é **ser melhor**,
   não empatar.
5. **O `rolhama` caiu e não vai voltar: custava manter ligado.** Todo recurso que passava por
   ele sai do roadmap ativo e vai para **§8**: transform `ia.extrair`, bot `entidades` e o
   **report PDF**. O código **não é apagado** — fica parado, e o que ele exige é anunciado como
   indisponível, não como erro feio. Substituto imediato e **sem IA nenhuma** para a extração de
   vínculos: a **menção não-linkada** (§4.4), que trabalha sobre o texto que já está no banco.
6. **Os diagramas são a prioridade agora.** A fase visual (§3) passa à frente do grafo vivo
   (§4): com o report morto, **o diagrama exportado é a entrega do trabalho**, e hoje não há como
   exportá-lo. Escopo desta rodada: os **três diagramas que já existem** ficando bons — tipo novo
   de diagrama (mapa geográfico, fluxo de dinheiro) **não** entra, fica para §5.
7. **SVG: a gente gera, nunca aceita de fora, nunca serve inline.** O risco é SVG de
   procedência desconhecida, não o formato — o que o `QSvgGenerator` produz da nossa própria cena
   só tem `path`/`text`/`rect`. Então: **export local em PDF, PNG e SVG**; **`Document` anexado só
   em PDF e PNG** (o diretório de `Document` não pode virar endpoint que serve `image/svg+xml`,
   senão um SVG de upload cai no mesmo lugar); **imagem de entidade só raster**, validada por
   bytes mágicos. Ver §3.2 e §3.6.
8. **A visão web leva um PNG de instantâneo** anexado no save (opção 1), e **não** uma tabela
   declarativa de regras de desenho compartilhada com o JS (opção 2, recusada). O canvas JS segue
   com implementação própria: **cada item do bloco B tem de ser espelhado à mão** lá.
9. **A lei do workspace foi reescrita** (`workspace/CLAUDE.md`): de "todo acesso a LLM passa pelo
   rolhama" para **"LLM é local e sob demanda"** — nenhuma API em nuvem (absoluto), modelo na
   máquina de quem trabalha, nenhum serviço de IA de pé esperando trabalho, degradar é
   obrigatório, agente MCP é caminho legítimo. Detalhe em §8.1.

## 1. Contra quem estamos

### 1.1 O que cada um faz bem (e é de onde se copia)

| Sistema | A força dele |
|---|---|
| **Maltego** | **Transform**: de uma entidade sai consulta e voltam entidades novas. Menu de contexto por tipo, *machines* (transforms encadeados), layouts automáticos, seleção em massa |
| **Obsidian** | O grafo **nasce da escrita**: `[[wikilink]]` dentro da nota *é* a aresta. Backlinks, **menção não-linkada** (o texto cita algo que ainda não é link), grafo **local** de profundidade N, busca instantânea com operadores, tags |
| **Siren** | **Investigação em escala**: grafo + dashboard de agregação + timeline + mapa geográfico na mesma tela, expansão de nó **com teto e top-N**, navegação relacional entre bases, alerta por watcher |

### 1.2 O que só o CML tem — e que não se negocia

- **Data em tudo, como período com formato de exibição** — caixa, vínculo (por ponta),
  classificação, entidade e referência.
- **Referência datada = acontecimento**: a fonte é também o fato, e alimenta a timeline
  (6 origens de data).
- **Entidade global com deduplicação** (`merge_to`), origem reversível pelo formato do `id`
  (UUID = MISP, `hex_hex_hex` = nativa), ~7.900 entidades de CTI já semeadas.
- **Organograma** e **timeline** como documentos irmãos do mapa.
- **Federação** entre servidores CML.
- **Curadoria obrigatória**: nada entra no mapa sem passar pelo painel Proposta.
- **Regras editoriais** escritas (`EDITORIAL.md`) — nenhum dos três tem opinião sobre o que
  é um bom mapa.

### 1.3 Os três eixos em que ganhamos

Isto é a espinha do SPEC. Cada fase abaixo serve a um destes eixos; recurso que não serve a
nenhum deles é candidato a sair.

1. **Procedência em toda afirmação.** Toda entidade, vínculo, data e nota carrega referência com
   URL e data de coleta, e o grafo sabe responder *"por que eu acho isso?"*. O Maltego esquece de
   onde veio assim que o transform termina; o Obsidian não tem o conceito; o Siren mostra o
   registro de origem, mas não a cadeia curada por um humano.
2. **O tempo como eixo, não como atributo.** Com data em seis lugares, o CML pode **reconstruir o
   grafo em qualquer data** — "como era a rede em março de 2024". Nos três, data é coluna de
   filtro; nenhum encolhe o grafo no tempo. É a **régua do tempo** da Fase 4 (§4.6).
3. **Descoberta automática e curadoria no mesmo lugar.** O Maltego despeja; o Obsidian é 100%
   manual; o Siren é 100% dado vivo. No CML o robô **propõe** e a pessoa aceita — e o aceite fica
   registrado (quem, quando, de qual fonte).

### 1.4 Tabela de lacunas

| Capacidade | Quem já tem | CML hoje | Fase |
|---|---|---|---|
| Transform: entidade → consulta → entidades/vínculos | Maltego | **feito**, não validado na tela | 1 |
| Menu de contexto por tipo de entidade | Maltego | **feito** | 1 |
| **Zoom, pan e rolagem no mapa** | todos | **inexistente** — pixmap fixo 5000×3000, sem `QScrollArea` | **2** |
| **Exportar o diagrama (PDF/PNG)** | todos | **inexistente** — `save(filename)` ignora o nome | **2** |
| Layouts automáticos | Maltego, Obsidian, Siren | posição manual | 2 |
| Peso de vínculo, tamanho por centralidade | Maltego, Siren | inexistente — `QPen` de largura fixa 1 | 2 |
| Colapsar grupo de caixas | Maltego, Siren | ✅ feito | 2 |
| Filtro, busca no canvas e seleção em massa | Maltego, Siren | ✅ feito | 2 |
| Caminho entre duas entidades | Maltego, Siren | inexistente | 2 |
| **Régua do tempo: diagrama reduzido a uma data** | **ninguém** | as datas já existem | **2** |
| Grafo local (vizinhança de profundidade N) | Obsidian, Siren | inexistente — `entity_simple_association` **sem UI** | 3 |
| Backlinks ("onde esta entidade aparece") | Obsidian | inexistente | 3 |
| Menção não-linkada | Obsidian | inexistente | 3 |
| Busca com operadores, sinônimos e relevância | Obsidian, Siren | `LIKE` em 2 colunas, **sem `LIMIT`**, ignora `entity_aka` | 3 |
| Nota longa que vira aresta (`[[wikilink]]`) | Obsidian | `description` é `LONGTEXT`, mas texto solto | 3 |
| Expansão com teto e top-N | Siren | inexistente | 3 |
| Transform em lote e machines | Maltego | inexistente | 3 |
| Dashboard de agregação junto do grafo | Siren | inexistente | 4 |
| Mapa geográfico | Siren | países com bandeira + transform `nominatim`, sem coordenada | 4 |
| Alerta ("avise se mudar") | Siren | inexistente | 4 |
| Auditoria de quem aceitou o quê | — | inexistente | 4 |
| Importar/exportar CSV, GraphML, STIX 2.1 | Maltego, Siren | ✅ feito (STIX só exporta) | 5 |
| Vault Markdown (entra e sai) | Obsidian | inexistente | 5 |
| Colaboração em tempo real | Siren | trava consultiva por mapa | 5 |
| Extração de entidades por IA | Maltego (hub), Siren | **parado** — era `rolhama` | **8** |
| Report narrativo automático | Siren (relatório) | **parado** — era `rolhama` | **8** |
| Hub/loja de transforms de terceiros | Maltego | — | fora de escopo |

## 2. Fase 1 — Transforms (implementada; falta validar)

### 2.1 Conceito

Um **transform** é uma função `(entidade de entrada) → lista de entidades + vínculos`.
O analista dá botão direito numa caixa do mapa, escolhe o transform da lista filtrada pelo
`etype`/`sub_etype` da caixa, e o resultado aparece **como proposta** (§2.4) — nunca grava
direto no mapa.

### 2.2 Contrato do plug-in

Reaproveita o desenho de `app/bot/<pais>/<nome>/` (um `config.json` + um módulo carregado por
`importlib`), mas **sem diálogo obrigatório**. Local: `app/transform/<fonte>/<nome>/`.

`config.json`:
```json
{
  "id": "dns.registros",
  "nome": "Registros DNS",
  "versao": "1",
  "entrada": ["other:dominio"],
  "saida": ["other:ip"],
  "fonte": "api-aberta",
  "rede": true,
  "rota": "direta",
  "chave_env": null,
  "ttl": 86400,
  "path": "transform.py",
  "class": "TransformDnsRegistros"
}
```
- `entrada`: lista de `etype` ou `etype:sub_etype` aceitos (filtra o menu).
- `fonte`: `base-propria` | `api-aberta` | `ia` | `scraping` — rótulo e agrupamento no menu.
- `rota`: `direta` | `tor` | ausente (usa `CML_TX_ROTA_PADRAO`); ver §6.
- `rede`/`chave_env`: para o menu avisar *antes* de executar que vai sair da máquina e que a
  chave falta.

Módulo: classe com `executar(entrada: dict, ctx) -> Resultado`, **sem Qt**, testável com
`python3` direto (padrão do `fussador`: núcleo × casca). `ctx` entrega `ctx.http()`, `ctx.llm()`
(**indisponível enquanto o rolhama estiver fora** — §8), `ctx.craudio()`, `ctx.cache`, `ctx.log`,
`ctx.ref()`.

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
**Toda informação gerada carrega referência** (URL da fonte + data de coleta na *descrição* da
referência, nunca em `start_date`) — é o eixo 1 do §1.3.

### 2.3 Famílias de transform

1. **Base própria** — `Entity.search`, `Entity.associations`, `entity_simple_association`.
   Sem rede externa, sem vazar a consulta. É onde a Fase 2 mais cresce.
2. **APIs abertas** — 18 conectores em `app/transform/api_aberta/` (catálogo em `docs/OSINT.md`).
   Cada um declara `chave_env` quando precisa.
3. **IA** — **parado em §8** (era `rolhama`). O `ia.extrair` continua no disco e falha com
   mensagem clara.
4. **Scraping (`craudiowebot`)** — job JSON pelo contrato do `craudiowebot/SPEC.md` (modo
   `--servir`, socket TCP). Mudança de comportamento lá exige atualizar o SPEC dele.

### 2.4 Fluxo de resultado: proposta, não gravação

Curadoria humana é o diferencial do CML; transform automático despeja lixo se gravar direto.
- O resultado abre o painel **Proposta**: caixa de seleção por entidade e por vínculo,
  origem/fonte visível, **marcação de duplicata**.
- **Buscar antes de criar:** para cada entidade proposta, o cliente chama `Entity.search`; se
  achar, oferece *reaproveitar o id existente* (padrão) ou *criar nova*.
- Aceitar = inserir caixas/vínculos no mapa aberto. Persistência só no **save do mapa** (igual ao
  `incorporate`); mapa travado não aceita.
- Entidade criada por transform recebe `id` nativo (`hex_hex_hex`), nunca UUID (reservado ao MISP).

### 2.5 Execução, cache e log

- `QThread` próprio (princípio do `ReportManager`: a thread não pertence ao diálogo). Cancelável;
  timeout por transform.
- Cache local em `~/.cml_cache/` por `(transform_id, versao, hash(entrada))` com `ttl` do
  `config.json`.
- Log local de execução — única trilha de auditoria que a decisão 3 permite; não vai ao servidor.

### 2.6 UI

Submenu **Transforms** no botão direito do `mapa_relationship_engine.py`, agrupado por `fonte`,
item indisponível visível com o motivo (falta chave, mapa travado, backend fora). Painel
**Proposta** e indicador de execução em andamento.

## 3. Fase 2 — Os diagramas (prioridade do dono, 2026-10-05)

**Por que subiu na frente:** o report PDF morreu com o `rolhama` (§8), e com ele a entrega
automática do trabalho. **A entrega passou a ser o diagrama** — e hoje não existe como tirá-lo
de dentro do app. Isso tira o export de "seria bom" e o põe como primeira coisa a fazer.

Estado real do canvas de vínculos, verificado no código:

- `MapaRelationshipEngine.__init__` faz `setFixedSize(5000, 3000)` e aloca um `QPixmap` do mesmo
  tamanho (~57 MB), **refeito inteiro a cada `mouseMoveEvent`** (o `redraw` preenche de branco e
  redesenha todos os elements).
- No `MdiMap`, **só a Timeline** é embrulhada em `QScrollArea`. Mapa de vínculos e organograma são
  widgets crus na subjanela do MDI: **sem rolagem e sem zoom**. Caixa arrastada para fora da área
  visível fica inalcançável.
- **Não existe exportar imagem.** `engine.save(filename)` **ignora o `filename`** e chama
  `self.mapa.save()` — a assinatura mente. E `engine.load(filename)` carrega uma imagem qualquer
  para dentro do pixmap e escala: código morto que, se chamado, apaga o desenho.
- O vínculo é **hiper-aresta** (caixa do verbo no meio, linhas retas de centro a centro —
  vermelhas para `to_entity`, azuis para `from_entity`) com `QPen` de **largura fixa 1**: sem
  peso, sem roteamento, linha passando por cima de outras caixas. O desenho em si é bom e fica.

### 3.1 A decisão de fundo: do pixmap para `QGraphicsView`

> ✅ **Implementado em 2026-10-05**, só no **mapa de vínculos** (organograma e timeline intactos,
> como esta seção previa). Um `ItemElemento` por element: `boundingRect` é a área pintada,
> `shape` é a área clicável, e no vínculo as duas diferem de propósito (pinta até as pontas,
> recebe clique só na caixa do verbo). Ganhos: rolagem, zoom por Ctrl+roda, arrastar a tela no
> vazio, menu de zoom no botão direito do vazio, antialiasing, e o fim do freio
> `(y % 2) == 0` do arrasto — ele existia só para aliviar o repinte do pixmap de 57 MB e fazia
> a caixa andar aos saltos. **Prova de que o desenho não mudou:** a cena renderizada bate
> **pixel a pixel (0 de 153.920 diferentes)** com a saída do exportador, que desenha direto do
> modelo sem passar pelo canvas. Teste: `QT_QPA_PLATFORM=offscreen python3
> app/test/mapa_relationship_engine.py`. **Falta:** seleção em massa por laço (bloco C) — os
> itens já nascem com `ItemIsSelectable`, então é ligar o `RubberBandDrag` sem conflitar com o
> arrasto de caixa.

Trocar o pixmap fixo por `QGraphicsView`/`QGraphicsScene`. Zoom, pan, minimap, seleção por laço,
z-order, hit test por item, cache por item e export vetorial deixam de ser seis gambiarras
separadas e passam a ser configuração do framework.

É barato de um jeito que normalmente não é: o modelo **já desenha com `draw(painter)`**
(`maprelationship_box.py`, `link.py`), então um `QGraphicsItem.paint()` fino delega para o mesmo
método — nenhuma regra de desenho é reescrita. A regra do projeto **"o layout mora no modelo"**
(como em `timeline.py`) continua valendo: o item Qt é casca.

Organograma e timeline **ficam fora desta rodada** — a timeline já tem o scroll e o zoom dela
funcionando, e mexer nos três canvas ao mesmo tempo é como se perde o controle do que quebrou.

### 3.2 Bloco A — o diagrama como entrega

**Export local: PDF vetorial (`QPdfWriter`), PNG em alta (render da cena em 2× ou 4×) e SVG
(`QSvgGenerator`).** O SVG serve para imprimir grande e para editar no Inkscape.

> ✅ **Implementado em 2026-10-05**: `app/classlib/exportar_diagrama.py` + ação **Exportar
> diagrama…** no menu File e na barra. Serve **os três diagramas**, e **não precisou da migração
> para `QGraphicsView`** — o modelo desenha com `draw(painter)`, e `QPdfWriter`/`QSvgGenerator`/
> `QImage` são todos `QPainter`. Teste: `QT_QPA_PLATFORM=offscreen python3
> app/test/exportar_diagrama.py` (monta mapa em memória, sem servidor; confere bytes mágicos e
> que rótulo `<script>` sai escapado no SVG). **Escala 1:1 paginada** e **escolha de papel na
> interface** entraram depois, no mesmo dia: o PDF reparte o desenho em N folhas A4/A3/A2 com
> marca "pág. 2/5" em cada uma, recortando o painter por página — sem o recorte o Qt desenharia
> o mapa inteiro em *toda* folha, porque o desenho não sabe que foi paginado. **Falta do bloco
> A:** o PNG de instantâneo anexado no save.

> ⚠️ **A linha onde o SVG para** (decisão do dono, 2026-10-05): o perigo é SVG **de procedência
> desconhecida**, não o formato. O que geramos da nossa cena só tem `path`/`text`/`rect` — e o
> `QSvgGenerator` escreve texto com escape de XML, então rótulo com `<script>` sai como texto
> desenhado (vale um teste quando chegar lá). Logo:
>
> - **Export para arquivo na máquina do analista: SVG pode.**
> - **`Document` anexado (que o app web serve): só PDF e PNG.** Não é o nosso SVG que assusta: é
>   que o diretório de `Document` viraria um endpoint servindo `image/svg+xml`, e aí um SVG **de
>   upload** cai no mesmo lugar e executa na origem do CML (XSS armazenado).
> - **Imagem de entidade (`entity_image`/`entity_face`): só raster**, validada por bytes mágicos
>   (§3.5) — este é o caso literal de "alguém faz upload de SVG".
> - Se algum dia um SVG tiver de ser servido: `Content-Disposition: attachment` e
>   `X-Content-Type-Options: nosniff`, nunca inline.

- Margem, título, data, **legenda** (tipos, cores, origens) e opção de anexar a lista numerada de
  referências — parte do que o report fazia em texto, o diagrama passa a fazer em desenho, **sem
  IA nenhuma**.
- Papel A4/A3/A2, com "caber na página" × "1:1 em N páginas".
- O PDF entra bem no pipeline que já existe: o `Document` **valida a assinatura `%PDF-`** em vez
  de confiar na extensão.
- **Se o PNG for anexado como `Document`**, a checagem no servidor precisa de um ramo para PNG
  **por bytes mágicos** (`\x89PNG\r\n\x1a\n`), e o `document_download.php` deve sair com
  `Content-Type` derivado da assinatura verificada, `X-Content-Type-Options: nosniff` e
  `Content-Disposition: attachment`.

**A visão web (decisão do dono, 2026-10-05):** anexar um **PNG de instantâneo** no save do mapa,
como "foto do mapa naquele dia". A alternativa — tabela declarativa de regras de desenho lida
pelos dois lados — **foi recusada**. Consequência a aceitar de olhos abertos: o canvas JS
(`server/webpage/view/relationship/relationship.php`) **continua com implementação própria das
regras de desenho**, então **cada item do bloco B precisa ser espelhado à mão lá**, ou os dois
divergem calados.

### 3.3 Bloco B — o diagrama legível

- **Layouts automáticos como ação**, não modo permanente: orgânico (force-directed), hierárquico,
  circular, bloco. Com desfazer — a posição manual do analista é dado, não enfeite. Mora no
  modelo, como o layout da timeline.
- **Espessura do vínculo pelo peso**, com valor editável **e** valor **derivado do número de
  referências** que o sustentam: vínculo com três fontes desenha mais grosso que o de uma. É o
  eixo 1 (§1.3) virando desenho. ⚠️ **Exige migração de banco** (coluna nova em
  `diagram_relationship_link`) — ver a regra abaixo.
- **Tamanho da caixa por centralidade** (grau), calculado no cliente, sem lib externa — como um
  viewlet, ver abaixo.
- **Roteamento que não atravessa caixa** e **data da ponta desenhada na linha**.
- ✅ **Colapsar grupo** (feito em 2026-10-05) — a *collection* do Maltego, para o mapa de 200
  caixas deixar de ser ilegível. É **vista**, como o ocultar: o documento não sabe que existe
  grupo, nada entra no desfazer e nada é salvo. A caixa do grupo **redesenha os vínculos que
  atravessam a fronteira** — sem isso o grupo apareceria desligado do resto, e o analista
  concluiria que aquele punhado de caixas não se liga a nada —, juntando numa linha só os que vão
  para o mesmo alvo pelo mesmo verbo, com a contagem. E ela **foge de quem ficou na tela**: o
  centro dos membros parece o lugar óbvio, mas numa estrela é exatamente onde está o hub, e como
  o grupo desenha por cima ele engoliria a caixa mais importante do mapa. Duplo clique expande.
- ✅ **List View** (feito em 2026-10-05): o mapa em **tabela**, alternando com o desenho na mesma
  janela (`view/ui/lista_diagrama.py`, botão **Lista**). Duas abas, porque no CML o vínculo também
  é element e as colunas dele são outras: **Entidades** (tipo·subtipo, nome, apelido, grau,
  período, refs, classificações, descrição) e **Vínculos** (verbo, de, para e um **período por
  ponta**). Ordena por valor nas colunas de número, começa pelos **mais ligados**, duplo clique
  abre o diálogo do objeto, e data suja (`0000-00-00`) vira célula vazia em vez de célula
  mentirosa. É vista, não editor: não grava nada.
- ✅ **Viewlets** (feito em 2026-10-05) — `classlib/relationship/viewlets.py`, botão **Vista**.
  Mecanismo, não lista de regras no meio do desenho: cada viewlet devolve, por caixa,
  `(escala, cor)`. Saem dele *tamanho por vínculos*, *por **entity rank*** (os próprios mais a
  soma dos vizinhos — acha quem liga poucos mas importantes), *por referências* (a procedência
  virando desenho), *cor por tipo* e **cor: sem fonte**, que é a regra do `EDITORIAL.md` virando
  cor. A cor é pintada como **moldura atrás** da caixa, porque o `draw` de cada tipo já preenche
  o próprio retângulo; e a ampliação vale também para a **área clicável**, senão a caixa cresce e
  só recebe clique no tamanho antigo.
- **Layout ortogonal** além dos quatro acima: entidades alinhadas em grade, que é o que o Graph
  Browser novo do Maltego pôs no lugar do *block*. É o que melhor serve a mapa impresso.
- **Ocultar sem apagar.**

### 3.4 Bloco C — o diagrama que pensa

- **Régua do tempo** — o item que nenhuma das três réguas tem: controle de data (ponto ou
  intervalo) que **reduz o diagrama ao que existia naquela data**, usando as datas que já estão em
  caixa, vínculo (por ponta), classificação, entidade e referência. Sem data = sempre visível,
  **com marcação de "sem data"**: ocultar calado o que não tem data é mentir sobre o mapa.
- **Caminho entre duas entidades** realçado — pergunta clássica de investigador; Maltego e Siren
  têm.
- ✅ **Busca no canvas** (feito em 2026-10-05): Ctrl+F procura por nome, apelido ou sub-tipo,
  seleciona todos os achados e centraliza no primeiro.
- ✅ **Minimapa** (feito em 2026-10-05): um segundo `QGraphicsView` sobre **a mesma cena** —
  clonar os itens daria duas verdades sobre o desenho. Mostra o que está visível escurecendo o
  resto (num mapa grande o contorno some, a sombra não) e clicar nele leva até o ponto.
- ✅ **Copiar/colar entre mapas** (feito em 2026-10-05) — `classlib/relationship/transferencia.py`,
  Ctrl+C/Ctrl+V. Viaja como **texto JSON** na área de transferência do sistema, com cabeçalho
  próprio: funciona entre janelas e entre duas execuções do CML, e texto de outra origem é
  recusado sem susto. **Colar não duplica a entidade** — cria caixa nova com o **mesmo
  `entity_id`**, porque entidade é global; duplicar criaria um gêmeo para o `merge_to` juntar
  depois. Vínculo só viaja com **as duas pontas** na seleção: meia aresta colada vira ponta
  solta no destino. Tudo num passo de desfazer, e o que entrou fica selecionado.
- ✅ **Ocultar sem apagar** (feito em 2026-10-05): estado de **vista**, não do documento — não
  entra no desfazer e não é salvo. Ocultar uma caixa esconde também os vínculos que a tocam
  (senão a linha iria até uma caixa fora da tela), o oculto não recebe clique "no escuro", e a
  **busca revela** o que estiver escondido — achar e não mostrar faria o analista concluir que a
  caixa não existe.
- ✅ **Seleção em massa** (feito em 2026-10-05), que é a base do transform em lote (Fase 3):
  laço com o botão esquerdo no vazio, Shift para somar, arrastar move o **grupo inteiro** em um
  passo de desfazer, Delete apaga a seleção. Arrastar a tela mudou para o **botão do meio**,
  porque o laço vale mais no esquerdo. Apagar vai em **ordem de dependência dentro da seleção**:
  os vínculos escolhidos perdem as pontas e saem primeiro, depois as caixas que nenhum vínculo
  restante referencia; caixa presa a vínculo que ficou **fora** da seleção é barrada e contada,
  nunca apagada por tabela.

### 3.5 Toda alteração de banco vem com script de migração

**Regra do dono, sem exceção:** o deploy **não altera banco** (`DEPLOY.md`), e **não se sabe
quantas instalações já existem** lá fora. Então toda coluna ou tabela nova entra **também** como
bloco de migração no fim de `server/data/create.sql`, do jeito que os anteriores já estão —
instalação nova sai correta pelo `create.sql`, instalação antiga roda o bloco à mão, uma vez.
Mudança de banco sem bloco de migração é defeito, não pendência.

Nesta fase, quem mexe no banco: o **peso de vínculo** (§3.3). O resto do bloco A é cliente
escrevendo arquivo — **o export não toca no banco**. Nas fases seguintes: índice `FULLTEXT` da
busca (§4.5), `[[wikilink]]` gravando em `entity_simple_association` (§4.6), a fila de propostas
persistida (§8.2) e a coordenada geográfica (§5).

### 3.6 Endurecimento de imagem, que vai junto

- **Bytes mágicos antes do `loadFromData`**: hoje o `QPixmap.loadFromData` detecta pelo conteúdo,
  então um blob SVG em `entity_face` seria entregue ao parser de SVG do Qt se o plugin estiver
  presente. Não executa script, mas é superfície de parser (XXE, expansão de entidade) sem
  motivo. Conferir `\xFF\xD8\xFF` (JPEG) ou `\x89PNG` e recusar o resto — o que também torna
  explícito qual formato o banco guarda.
- **Já verificado seguro, e fica assim:** o data URI do canvas JS tem MIME de **lista fixa**
  (`relationship.php:156`) — `image/jpeg` se o base64 começa com `/9j/`, senão `image/png`,
  **nunca `image/svg+xml`**. Navegador não fareja além do MIME declarado num `data:` dentro de
  `<img>`, então blob SVG ali falha em decodificar em vez de executar.

## 4. Fase 3 — O grafo vivo e a descoberta em lote

**A premissa:** o banco **já é** um grafo global — `entity_simple_association` (MISP), mais todo
vínculo de todo mapa, mais classificações e referências compartilhadas — e **não existe uma única
tela que o mostre**. Esta fase é a de maior retorno por linha escrita, é toda em base própria
(sem rede, sem IA, **sem rolhama**) e é o que o usuário de Obsidian reconhece na hora.

### 4.1 `Entity.neighborhood` no servidor

Método novo: vizinhança de profundidade N de uma entidade, de **quatro origens**, cada aresta
dizendo de qual veio:

| Origem | De onde |
|---|---|
| Associação global | `entity_simple_association` (hoje sem UI) |
| Vínculo em mapa | `diagram_relationship_link` + elements de qualquer mapa |
| Mesma classificação | `entity_classification_item` |
| Mesma referência | `diagram_relationship_element_reference` |

**Com teto, sempre** (lição do Siren): `limite_por_nivel` e `limite_total`, e quando corta,
devolve os **top-N por grau** mais o aviso de quantos ficaram de fora. Expansão sem teto num
banco de 7.900 entidades trava o cliente.

### 4.2 Janela Vizinhança (grafo local)

Abre de qualquer entidade, **não é documento**: não tem nome, não salva posição, não entra na
lista do Open. É exploração — profundidade 1–3, filtro por origem de aresta e por `etype`. Dali o
analista **arrasta para um mapa curado**, e aí sim vale o caminho normal (Proposta → save).
A distinção *exploração × documento* é o que o Obsidian não faz (lá o grafo é enfeite) e o
Maltego também não (lá todo grafo é descartável).

### 4.3 Aba "Onde aparece" (backlinks)

No diálogo de qualquer entidade: em quantos **mapas** ela está, em quantos **vínculos**, em
quantas **referências**, com que **classificações** — duplo clique abre. É a primeira pergunta de
um analista e hoje não há como responder.

### 4.4 Menção não-linkada — o substituto do `ia.extrair`, sem IA

O truque mais útil do Obsidian, e aqui vale mais: varrer o `description` (`LONGTEXT`) e os
títulos/descrições de referência procurando `text_label` e `entity_aka` de **outras** entidades;
cada acerto é um **vínculo proposto**, com a frase onde apareceu como justificativa, no painel
Proposta.

É um **transform de base própria** (`base.mencoes`): zero rede, zero chave, zero LLM — portanto
**não depende do rolhama**. Cuidados: casar palavra inteira, respeitar maiúsculas/minúsculas de
sigla, ignorar nome curto demais (< 4 caracteres) e a própria entidade, e **nunca** gravar sem
aceite.

### 4.5 Busca que presta

Hoje `Entity.search` é `LIKE` em `text_label`/`small_label`, **sem `LIMIT`**, e **ignora
`entity_aka` e `description`** — com 7.900 entidades, buscar "a" devolve o banco inteiro pela
rede. Trocar por:

- índice **`FULLTEXT`** em `text_label`/`small_label`/`description` + busca em `entity_aka`;
- operadores: `etype:person`, `classificacao:"Diretor"`, `periodo:2019..2022`, `-palavra`;
- `LIMIT` com ordenação por relevância, e contagem total separada;
- fallback para `LIKE` quando o `FULLTEXT` não existir no banco (instalação antiga).

Migração de banco obrigatória (padrão do projeto: bloco no fim de `server/data/create.sql`).

### 4.6 Nota longa com `[[wikilink]]`

`description` já é `LONGTEXT`: falta o editor (`QEditorPlus`) aceitar `[[nome da entidade]]` com
completar-ao-digitar, e o save resolver cada wikilink em `entity_simple_association`. **Escrever a
nota passa a construir o grafo** — o laço do Obsidian, mas dentro de um modelo que tem tipo, data
e fonte. Wikilink para nome que não existe fica pendente e aparece na Proposta como "criar".

### 4.7 Descoberta em lote (o que sobrou do Maltego)

Depende da **seleção em massa** (§3.4), por isso vive aqui e não na fase dos diagramas.

- **Transform em lote** sobre a seleção, com teto explícito de entidades por passo.
- **Machines**: sequência de transforms em JSON, com profundidade e limite por passo. Sem limite,
  uma machine explode o mapa — o teto é parte do contrato, não opção.

## 5. Fase 4 — Painel do investigador (o que se tira do Siren)

1. **Dashboard junto do grafo** (não em outra tela): contagem por `etype`, por classificação, por
   década, top entidades por grau, referências agrupadas por domínio de origem. Clicar na barra
   **seleciona no mapa**.
2. **Mapa geográfico**: já existem países com bandeira (`script/country_seed.py`) e o transform
   `nominatim`. Falta coordenada na entidade — cabe em `data_extra` (`LONGTEXT` livre) ou em
   colunas `lat`/`lon` próprias; decidir na hora, preferindo coluna se for filtrar por caixa
   geográfica.
3. **Alerta local**: "avise quando esta entidade ganhar vínculo ou referência nova". O servidor é
   JSON-RPC sem push, então é **polling do cliente** — e isso se diz na interface, sem fingir
   tempo real.
4. **Auditoria da curadoria**: quem aceitou qual proposta, de qual transform, quando, e o que foi
   recusado. Fecha o eixo 1: o mapa passa a saber contar a própria história.

## 6. Fase 5 — Dados e colaboração

- ✅ **Exportar CSV, GraphML e STIX 2.1** (feito em 2026-10-05) — `classlib/exportar_dados.py`, menu File →
  **Exportar dados…**. O `exportar_diagrama.py` tira a figura; este tira a informação, que era o
  que faltava para levar a investigação a outra ferramenta (Gephi, yEd, Cytoscape, planilha).
  **CSV são dois arquivos** (entidades e vínculos), pela mesma razão das duas abas da List View.
  A **hiper-aresta vira uma linha por par**, porque planilha e GraphML não sabem o que é isso, e
  o `grau` exportado conta **arestas expandidas** — contar vínculos deixaria o nó discordando do
  próprio arquivo quando aberto no Gephi. As datas e a contagem de referências vão como atributo:
  mapa sem data e sem fonte perde justamente o que o CML tem de diferente. CSV sai em `utf-8-sig`
  porque o destino número um é o Excel.
- ✅ **STIX 2.1** (feito em 2026-10-05): bundle com `identity`/`threat-actor`/`malware`/`tool`/
  `location`/`vulnerability` conforme o **sub-tipo**, que é o que as entidades semeadas do MISP
  Galaxy carregam; o que não é reconhecido vai como `identity`/`unknown`, válido e honesto —
  inventar um tipo `x-cml-*` faria metade das ferramentas ignorar. **Entidade de origem MISP tem
  `id` em formato UUID** (convenção do projeto), e esse UUID é **reaproveitado** no id STIX, então
  o mesmo ator exportado daqui e de outra ferramenta casa pelo id; entidade nativa ganha `uuid5`
  determinístico. Vínculo vira `relationship` com `start_time`/`stop_time` das pontas.
- ✅ **Importar CSV e GraphML** (feito em 2026-10-05) — `classlib/importar_dados.py`. O arquivo
  **não entra direto no mapa**: é lido para um `Resultado` (a mesma estrutura que um transform
  devolve) e entregue ao painel **Proposta**, que já faz buscar-antes-de-criar e oferece
  reaproveitar a entidade existente. Era o único jeito de importar sem furar duas regras de uma
  vez — "entidade é global" e "curadoria humana": um importador próprio criaria uma entidade nova
  por linha, e 300 linhas virariam 300 duplicatas para o `merge_to` limpar. As colunas são
  reconhecidas por **nome** (várias grafias, pt e en), o delimitador é detectado, e planilha só de
  vínculos cria também as pontas. O `aplicar` passou a aceitar **origem `None`** para isso.
- **Falta**: importar STIX.
- **Vault Markdown (Obsidian) nos dois sentidos**: importar um vault (nota → entidade,
  `[[wikilink]]` → vínculo, frontmatter → classificação) e exportar um mapa como vault. É como se
  traz quem já trabalha em Obsidian.
- **Histórico navegável** — `diagram_relationship_history` já acumula o JSON inteiro de cada save
  e nenhuma tela o lê.
- **Colaboração** em lugar da trava consultiva: decisão grande, exige estudo próprio.

## 7. Decisões de rede e questões abertas

**Resolvidas (2026-10-02)**
- **Ordem das APIs abertas:** Wikidata, crt.sh, DNS primeiro (feito; hoje são 18 conectores).
  Portal da Transparência entra quando o domain `corrupcao` pedir (exige `CML_TX_TRANSPARENCIA_KEY`).
- **Rede no Qubes:** o transform **declara** a rota no `config.json` — `"direta"` (qube de rede) ou
  `"tor"` (`sys-whonix`) — e o cliente usa o proxy correspondente (`CML_TX_PROXY_DIRETA`,
  `CML_TX_PROXY_TOR`). O padrão da estação é `CML_TX_ROTA_PADRAO`; o `config.json` só fixa a rota
  quando a fonte exige. Transform `rede: true` sem rota resolvível não executa e diz por quê.
  Na rota `tor`, o DNS também sai pelo Tor (`socks5h`), por isso DNS é via DoH.

**Adiada:** campo de **confiança** (0–100) por vínculo — reavaliar junto do **peso derivado**
(§3.3), que pode torná-lo redundante.

**Aberta:** se a coordenada geográfica vira coluna em `entity` ou vive em `data_extra` (§5.2).

## 8. IA depois do `rolhama` (2026-10-05)

Nada aqui está no caminho crítico — exigência do ponto 5 da lei nova. **O código não é
apagado**; o que depende de LLM anuncia indisponibilidade com mensagem clara, em vez de estourar
exceção na cara do usuário. O caminho de volta está em §8.1.

| Recurso | Onde está | O que fazer agora |
|---|---|---|
| Transform `ia.extrair` | `app/transform/ia/extrair/` | fica no disco; o menu mostra "indisponível: backend de LLM fora" |
| Bot `entidades` | `app/bot/brazil/entidades/` | mesmo tratamento no botão do diálogo |
| **Report PDF** | `app/classlib/report.py`, `view/ui/report_manager.py`, `server/.../ReportJob/001.php` | o botão **Documents** deve dizer que a geração está suspensa; a trava global no servidor e a tabela de job ficam como estão (documento já gerado continua abrindo e baixando) |
| `ctx.llm()` | `app/transform/contexto.py` | erro claro de backend ausente |
| Canais 507/510 | `CANAL_POR_PROJETO` | sem efeito enquanto não houver worker |

### 8.1 O backend novo: Ollama local, e o agente MCP

**A lei do workspace mudou em 2026-10-05** (`workspace/CLAUDE.md`, "LLM é local e sob demanda"):
o `rolhama` foi revogado como caminho obrigatório porque **custava manter ligado**. O que a lei
nova manda: nenhuma API em nuvem (absoluto), modelo na máquina de quem está trabalhando, nenhum
serviço de IA de pé esperando trabalho, degradar é obrigatório, e **agente MCP é caminho
legítimo**. Logo, o que estava em FUTURO não está mais bloqueado por falta de lei — está
bloqueado por três itens de código, abaixo.

**Duas portas para o mesmo Ollama**, porque o critério é quem dispara:

| Caminho | Quem dispara | Como |
|---|---|---|
| Botão da interface (report, bot) | o analista, no PySide6 | `CML_LLM_BACKEND=ollama` + `CML_OLLAMA_URL` — **já existe no código**, é uma variável de ambiente |
| Exploração conduzida | o dono, num terminal | **OpenCode com Ollama** falando com o servidor MCP `cml-transforms` (bloco `mcp` do `~/.config/opencode/opencode.json`, `"type": "local"`) |

O que falta para a porta do MCP valer:

1. **Login sem Qt no servidor MCP** (§9 item 7). Hoje `mcp/cml_transforms.py` não tem nada de
   sessão/handshake RSA, então `base.parecidas` e `base.associadas` — justamente os que a Fase 2
   faz crescer — não funcionam por ele.
2. **Fila de propostas persistida.** O MCP é `proposta_somente` de propósito, e o painel Proposta
   só existe na memória do cliente. Proposta vinda do agente precisa pousar onde a GUI leia
   depois. **Isso é prêmio, não custo** — ver §8.2.
3. **Ferramenta de extração de tiro único** (`extrair_entidades(texto|url) → Resultado`). Modelo
   local de 7–14B é bem pior em tool-calling encadeado do que em geração simples: conte com ele
   acertando "extraia entidades deste texto com `format=json`" (que é o que o `ia.extrair` fazia)
   e não com ele conduzindo dez passos de MCP sozinho. A inteligência fica no contrato da
   ferramenta, não na autonomia do agente.

Tamanho de modelo segue o ponto 4 da lei: 14B q6_K só quando a `.90` já estiver ligada por outro
motivo; na estação, 7–8B quantizado — que basta para extração de tiro único com `format=json`.

### 8.2 Curadoria assíncrona — o que a fila de propostas dá de graça

Persistir a proposta dá ao CML algo que **nenhuma das três réguas tem**: o robô propõe de noite,
o analista aceita de manhã, e fica registrado quem aceitou o quê e de qual fonte (eixo 1 do §1.3).
Maltego despeja na hora, Obsidian não propõe, Siren não cura. Por isso a fila sobe para dentro da
**Fase 3** (§4), e não fica esperando o backend de LLM: ela serve igualmente às propostas de
`base.mencoes` (§4.4) e dos 18 conectores OSINT, que não dependem de IA nenhuma.

**O que substituiu a IA no roadmap ativo:** a **menção não-linkada** (§3.4) faz, sobre o texto que
já está no banco, o que o `ia.extrair` fazia sobre texto da web — sem rede, sem chave, sem fila.

## 9. Estado e próximos passos

**Feito (2026-10-05):** export de diagrama em PDF, PNG e SVG (§3.2) — primeira entrega da
Fase 2, e o primeiro caminho pelo qual trabalho feito sai do app desde que o report morreu — e a
migração do canvas do mapa de vínculos para `QGraphicsView` (§3.1), que destravou rolagem e zoom.

**Feito (2026-10-02):** núcleo sem Qt (`app/transform/`), menu de contexto, painel Proposta,
aplicar em círculo com dedup, gerente em thread, cache/log locais, transforms `base.parecidas`,
`base.associadas`, `scraping.links_externos`, 18 conectores OSINT (`docs/OSINT.md`), servidor MCP
`cml-transforms` (`docs/MCP.md`), `Entity.associations` no PHP. Testes só headless/offscreen.

**Fila, em ordem:**

1. **Rodar o app de verdade** (`python3 app/application.py`, servidor real): botão direito →
   transform → Proposta → aplicar → salvar. **Nada disso foi visto na tela** — é o item que mais
   risco carrega, porque toda a Fase 1 depende dele estar certo.
2. **Deploy do servidor** (flag-portão do `DEPLOY.md`) para `Entity.associations`; testar
   `base.associadas`.
3. **Degradar o rolhama com elegância** (§8): mensagem de indisponível no menu de transform, no
   botão do bot e no botão **Documents**. Sem isso, o usuário encontra exceção.
4. **Fase 2 — os diagramas** (§3), que é a prioridade declarada do dono. Ordem revista na
   execução: **bloco A, export** (§3.2) ✅ **feito** — veio antes porque não depende da migração →
   `QGraphicsView` (§3.1) ✅ **feito** → endurecimento de imagem (§3.6) →
   bloco B, legibilidade (§3.3) → bloco C, começando pela régua do tempo (§3.4). Nada disso
   depende de rede, de IA nem de deploy.
5. **Fase 3 — o grafo vivo** (§4): `Entity.neighborhood` → janela Vizinhança → aba Onde aparece →
   **fila de propostas persistida** (§8.2) → `base.mencoes` → busca com `FULLTEXT` →
   `[[wikilink]]` → lote e machines. Também é tudo base própria.
6. **Backend de LLM local** (§8.1), quando o dono quiser a IA de volta: `CML_LLM_BACKEND=ollama`
   para os botões do app, **login sem Qt no MCP** e a ferramenta `extrair_entidades` de tiro único
   para o OpenCode.
7. Pontas soltas dos transforms: `Http.post()` público, corpo do erro não-200 (o 429 do GDELT),
   decidir se o aplicador cria subtipo de Other que falta (hoje só avisa), exercitar
   `abusech`/`virustotal`/`hunter` com chave real.
8. `scraping.links_externos` de ponta a ponta com o `craudiowebot --servir`.
9. Fases 4 e 5 (§5, §6).

## 10. Fora de escopo

Hub/loja de transforms de terceiros; execução de transform no servidor (descartada na decisão 3);
qualquer coleta que contorne autenticação ou termos de uso de uma fonte.
