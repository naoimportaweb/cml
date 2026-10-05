# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é isto

O CML é uma ferramenta de análise de vínculos dividida em duas partes: um **cliente desktop PySide6** (`app/`), que desenha mapas de relacionamento, organogramas e linhas do tempo, conversando com um **servidor PHP + MySQL** (`server/`) através de um endpoint JSON-RPC próprio. O código, os comentários e as mensagens de interface estão majoritariamente em português (pt-BR); mantenha essa convenção ao editar os arquivos existentes.

## Comandos

Não há build system, runner de testes, linter nem `requirements.txt`. As dependências são instaladas de forma imperativa.

```bash
# Prepara a máquina para rodar o cliente a partir do código (apt + pip)
./dependencias.sh

# Executa o cliente (mostra o diálogo de Connect/Login primeiro; encerra se o login falhar)
python3 app/application.py

# Empacota o servidor + o tarball do cliente em /tmp/server (precisa ser executado de dentro de script/)
cd script && ./deploy.sh
```

O `dependencias.sh` (raiz) é o bootstrap de **desenvolvimento**: instala as libs de sistema do plugin xcb do Qt6 — sem `libxcb-cursor0` o PySide6 ≥ 6.5 no Debian 13 morre com *"libxcb-cursor0 is needed to load the Qt xcb platform plugin"*, e o pip não traz essa lib — e depois as deps Python (`requests PySocks PySide6 pycryptodome pyspellchecker beautifulsoup4 waybackpy`, com `--break-system-packages` por causa do PEP 668 — o `PySocks` é o que faz a rota `tor` dos transforms funcionar). Não baixa nada do site nem exige servidor.

O `app/install.sh` é o instalador para o **usuário final**, não um comando de desenvolvimento: exige root, recebe a URL do site, baixa o `client.tar.gz` desse site, descompacta em `/opt/cml` e cria o symlink `/bin/cml`. A lista de deps Python vive nele e no `dependencias.sh` — mudou uma, mude a outra.

### Acesso ao servidor

O `.mcp.json` registra **dois** servidores MCP, de propósitos que não se misturam: `cml-remoto` (hospedagem: deploy, SQL, logs) e `cml-transforms` (descoberta de dados; ver `docs/MCP.md`). Os dois entram desligados pelo `disabledMcpjsonServers` do `.claude/settings.local.json` — habilite o que for usar antes de contar com as ferramentas.

Prefira o servidor MCP `cml-remoto` (`mcp/remoto_hostinger.py`) a montar `ssh`, `rsync` e `mysql` na mão: ele já carrega as regras do `DEPLOY.md`. `flag_confirmar` faz a checagem da flag antes de qualquer envio, `deploy` empacota e envia já com `--exclude data/` e sem `--delete`, `php`/`lint` usam o binário **8.5** (o `php` do PATH no SSH é 7.4 e **não** é o runtime de produção), `sql` manda a senha por stdin e recusa o irreversível, `log_ref` acha no `error_log` o SQL por trás de um erro que chegou ao usuário, e `ler_arquivo` recusa `.env`, chaves, certificados e o `data/config.json`. Lista das ferramentas em `DEPLOY.md`.

Credenciais vêm do `~/.env` da estação (`SSH_HOSTINGER_*`, `<PROJETO>_DEPLOY_*`, `<PROJETO>_DB_*`); **nunca** escreva segredo no `.mcp.json`, que é versionado. O servidor é o mesmo padrão do `aivalia-remoto` (`../aivalia/mcp/remoto_hostinger.py`) — a convenção do workspace é **copiar, não compartilhar** (como o `webapi.py`/`bdd.py` do rolhama), então os dois arquivos evoluem separados.

O procedimento completo de publicação em produção (Hostinger/LiteSpeed, a flag-portão do deploy, o `data/` que nunca é enviado) está em `DEPLOY.md` — leia-o antes de mexer no `deploy.sh` ou em qualquer coisa de deploy.

Hoje há **duas instalações** na mesma conta, uma por projeto do `~/.env`: `CYBERWARFARE` (domain `cyberwar`, em `/cyberwarfare`) e `CORRUPCAO` (domain `corrupcao`, em `/corrupcao`, criada em 2026-09-22 copiando os fontes da primeira). Domain novo **não** é uma linha a mais no `config.json` de quem já existe — é banco próprio (que só o hPanel cria) e, na prática, instalação irmã; a receita é o Passo 5 do `DEPLOY.md`, e o `script/domain_add.php` é quem inclui o domain no `config.json` (no servidor, senha por stdin).

Os recursos de report e o bot de entidades falam com um serviço externo (o **rolhama**) e leem segredos do `~/.env` (`ROLHAMA_BDD_KEY`, `ROLHAMA_WEBAPI_URL`/`ROLHAMA_BDD_URL`, etc.). Nada de valor concreto vai em arquivo versionado — sempre a variável, nunca o valor. Sem essas variáveis, o report simplesmente falha em runtime; o resto do app funciona.

Para subir o servidor: Apache + PHP com o diretório `server/` servido no caminho **`/cml`** da raiz web (o cliente tem `/cml/services/execute.php` fixo no código), o schema MySQL de `server/data/create.sql` e um diretório de certificados com permissão de escrita (`/var/certs/`, conforme `server/data/config.json`), onde o par de chaves RSA é gerado na primeira requisição.

### Testes

Não existe framework de testes; o que existe são scripts rodados direto com `python3`.

```bash
# Conectores OSINT contra a rede de verdade (sem chave; os que exigem chave só conferem a
# mensagem de erro). Sem argumento roda todos; com argumentos filtra por trecho do id.
python3 app/transform/testes_osint.py
python3 app/transform/testes_osint.py dns crtsh

# Servidor MCP cml-transforms de ponta a ponta, falando o protocolo por stdin/stdout.
# Não usa rede nem LLM; cria transforms de teste em diretório temporário.
python3 mcp/teste_cml_transforms.py
```

Fonte pública oscila: no `testes_osint.py`, falha de rede é **AVISO** e falha de contrato é **ERRO** — só o segundo é defeito nosso.

`app/test/user.py` e `app/bot/brazil/wikipedia/test.py` são scripts pontuais do código antigo. Atenção: `app/bot/brazil/wikipedia/test.py` tem um caminho `/home/well/...` fixo no código, que precisa ser editado antes de rodar.

## Arquitetura

### O envelope RPC — a espinha dorsal do sistema

Toda classe do cliente que fala com o servidor estende `ConnectObject` (`app/classlib/connectobject.py`) e chama `self.__execute__(class_name, method_name, parameters)`. Isso faz um POST de um envelope JSON para `{server}/cml/services/execute.php`:

```json
{"version": "001", "class": "Entity", "method": "search", "domain": "...", "session": "...", "parameters": "00000000{...json...}"}
```

O `server/services/execute.php` trata alguns métodos explicitamente (`Domain.list`, `Session.publickey|login|register`) e despacha todo o resto **dinamicamente**: faz `require_once` de `services/classlib/{class}/{version}.php` e chama `(new $class)->$method($ip, $user, $post_data, $domain)`.

Consequências a respeitar ao adicionar funcionalidade no servidor:

- Um método novo no servidor é um **método público com exatamente a assinatura de 4 argumentos** `($ip, $user, $post_data, $domain)`, lendo suas entradas de `$post_data["parameters"]`.
- O campo `version` é o **nome do arquivo**: `"001"` → `001.php`. Uma nova versão da API é um arquivo novo, não um desvio dentro do antigo.
- O nome da classe no envelope corresponde a um diretório em `server/services/classlib/`. Os nomes de classe no cliente e no servidor precisam ser idênticos.

O `parameters` é prefixado por uma tag de criptografia de 8 caracteres: `00000000` = JSON em texto puro, `00000001` = criptografado com RSA (base64). Os retornos seguem o mesmo padrão, `00000000` + base64 do JSON — o cliente descarta os 8 primeiros caracteres e decodifica o base64. O AES (`002`) está pela metade e desativado nos dois lados; `app/classlib/aes.py` e `server/api/aeshelper.php` são código morto/placeholder (o `decrypt` do PHP ignora completamente os argumentos que recebe).

### Domains = multi-tenancy

O `server/data/config.json` define os `domains`, cada um apontando para sua própria conexão MySQL em `connections`. O `new Mysql($domain)` seleciona o banco, de modo que **o mesmo código PHP atende vários bancos isolados** e todo método de serviço recebe `$domain`. Um domain `restricted` exige um token de convite válido (tabela `person_enter`) para cadastro.

Esse arquivo está versionado com credenciais padrão e é removido de propósito pelo `deploy.sh` (`rm -r /tmp/server/cml/data/*`); o `server/data/.htaccess` bloqueia todo acesso HTTP a ele.

### Camada de banco e contrato de erro do servidor

Todo acesso ao MySQL passa por `server/api/mysql.php` (`Mysql`): `Datatable` para consulta, `ExecuteNoQuery` para gravação (lista de SQLs numa transação). As conexões vivem num **pool estático por (host, banco, usuário)**, compartilhado por todas as instâncias de `Mysql` do mesmo request — o load de um mapa faz mais de cem consultas, e abrir uma conexão TCP por consulta era o que fazia a hospedagem compartilhada devolver `SQLSTATE[HY000] [2002] Operation not permitted` numa consulta aleatória, parecendo defeito da consulta. Não volte a soltar a conexão no `finally` de cada consulta.

A exceção que chega ao cliente **nunca carrega o SQL**: sobe só o **código** do erro do banco mais uma **ref.** de 8 hex; o SQL e os parâmetros ficam no `error_log` sob a mesma ref (`[abcd1234] Error: ...`), que é o que a ferramenta `log_ref` do MCP procura. O código **precisa continuar na mensagem**: o `ReportJob` reconhece a trava global tomada procurando `1062` no texto — mascarar tudo quebraria a trava em silêncio. No cliente, `MapRelationship.load` devolve `False` com a mensagem do servidor (a lista de mapas avisa por que não abriu) em vez de deixar o `MdiMap` montar um engine com mapa `None`, e os três engines fecham o painter num `finally`: sem isso o erro de desenho estoura dentro do `painter.begin()`, o processo cai em segfault e o erro real se perde junto.

### Federação

Um servidor CML pode consultar *outros* servidores CML. O `federation_proxy.php` (chamado pelo cliente via `ConnectObject.__proxy__`) distribui o mesmo envelope para cada servidor federado listado para o domain; o `federation.php` é o endpoint que recebe do outro lado e valida o par `Class.method` contra uma lista de permissões antes de despachar. O `Entity.search(..., proxy=True)` mescla os resultados locais e federados, marcando cada um com um campo `server`. As chamadas de federação não são autenticadas — o acesso é controlado apenas pela chave `federation_id` e pela lista de métodos permitidos no config.

### Autenticação e sessão

Handshake de três etapas em `app/classlib/user.py` + `server/services/classlib/session.php`: o `publickey()` devolve a chave pública RSA do servidor **e o salt do usuário**; o cliente calcula `sha256(password + salt)` e envia para o `login()`, que retorna um token de sessão. O token fica guardado no singleton `Server` e é anexado a todos os envelopes seguintes; o `execute.php` resolve esse token de volta para um usuário via `person_sesion` antes de despachar.

### Singletons e configuração do cliente

`Server` (`classlib/server.py`) e `Configuration` (`classlib/configuration.py`) usam `SingletonMeta` e são acessados por `.instancia()`. O `Server.ip` guarda a **URL base completa** (ex.: `http://localhost`), não um IP, apesar do nome. O `Configuration` persiste em `~/.cml.json`, com os padrões preenchidos pelo helper de caminho pontuado `__getParameter__`. Atenção ao `__save__`: ele **remonta o JSON do zero** a partir de campos fixos, então chave que não estiver ali é perdida no próximo save — foi por isso que o tamanho de janela virou um dicionário (`janelas`) com `getTamanhoJanela`/`setTamanhoJanela`, e não um par de campos por diálogo. A gravação acontece no `closeEvent` do diálogo, nunca no `resizeEvent`: arrastar a borda dispara dezenas de eventos por segundo, e cada um reescreveria o arquivo inteiro.

Todo módulo prepara o `sys.path` com `CURRENTDIR`/`ROOT` via `inspect.getfile` antes dos imports — é por isso que os imports são absolutos (`from classlib.x import Y`) e o app roda a partir de qualquer diretório. Mantenha esse preâmbulo ao criar módulos novos. Alguns diálogos (`dialog_connect.py`, `dialogreference.py`, `dialog_classification.py` e outros) ainda somam um `sys.path.append("/opt/cml/app/")` fixo, resquício do caminho de instalação; é inofensivo rodando do código, mas não copie isso para arquivo novo.

**Código morto que parece vivo:** o corretor ortográfico não funciona. O botão "Spell check" do `QEditorPlus` chama `MyHighlighter` → `Culture.errors` (`app/classlib/culture.py`), e o `from spellchecker import SpellChecker` de lá está **comentado** — clicar estoura `NameError`. O `pyspellchecker` continua na lista de dependências, e o `Culture("pt")` é fixo em português, ignorando o idioma do mapa. Consertar é reativar o import (e passar o idioma), não reescrever.

### Modelo de domínio

A `Entity` é o registro central (`app/classlib/entity.py`, `server/.../Entity/001.php`), com um `etype` que pode ser `person`, `organization`, `other` ou `link`. As entidades são globais e compartilhadas entre os mapas; o `merge_to` faz a deduplicação repontando todas as tabelas que as referenciam.

Além do `etype`, a entidade recebe **classificações datadas**. A taxonomia é global no banco — `classification` ("Cargo") → `classification_item` ("Diretor") — e **não tem tela de cadastro**: o cliente só a consulta (`Classification.search`, com `%like%` em `app/classlib/classification.py`), então taxonomia nova entra no banco à mão. O que é por entidade é a linha em `entity_classification_item`, com `start_date`/`end_date` e um `format_date` que decide como a data é exibida (aba **Classification** dos diálogos de entidade, alimentada por `DialogClassification`). Esse vínculo **é gravado no save do mapa** (o `MapRelationship/001.php` insere e apaga `entity_classification_item` junto com os elements), não por endpoint próprio — o `Classification.add` do servidor existe mas nenhum cliente o chama.

Um `MapRelationship` contém `elements`, que são caixas envolvendo entidades. **Os links também são elements**, com `etype == "link"`, carregando as listas `to_entity`/`from_entity` — por isso apagar uma caixa que participa de um link lança exceção em vez de fazer cascata. Os mapas são salvos como documento inteiro: o `save()` serializa o mapa mais o `toJson()` de cada element em uma única chamada, e cada save empilha o JSON inteiro em `diagram_relationship_history` (o histórico é só append; não há tela que o leia). Os mapas também têm trava consultiva (`lock_map`/`unlock_map`); um mapa travado fica somente leitura e o título da janela principal indica isso.

**Incorporar não é merge.** O `merge_to` da `Entity` é global: funde duas entidades no banco inteiro. Já o `MapRelationship.incorporate(destino, origem)` (botão *Incorporate* na aba **Actions** dos diálogos de entidade) é composição **dentro de um mapa só**: copia as referências de `origem` para `destino` (pulando `link1` já presente), reponta toda ponta `to_entity`/`from_entity` que apontava para a caixa `origem` e tira `origem` do mapa. A entidade global, o nome e o tipo do destino ficam intactos; vale só entre entidades (vínculo não incorpora) e nada persiste até salvar o mapa. Repontar antes de remover é o que evita a exceção do `delEntity`.

O `OrganizationChart` é a estrutura paralela para organogramas, com seu próprio engine de canvas. Os dois canvas ficam em `app/view/ui/mapa_relationship_engine.py` e `app/view/ui/mapa_organization_chart_engine.py` — e **não são mais iguais por dentro**: o do mapa de vínculos é um `QGraphicsView` (um `ItemElemento` por element, que lê `x`/`y`/`w`/`h` do modelo e pinta com o `draw()` dele), enquanto o do organograma segue no `QPixmap` de tamanho fixo. No `ItemElemento`, `boundingRect` é a área **pintada** e `shape` é a área **clicável**, e os dois diferem de propósito no vínculo: ele é hiper-aresta (caixa do verbo + linhas até cada ponta), então pinta até as pontas mas só recebe clique na caixinha do verbo — se o clique seguisse o `boundingRect`, o vínculo engoliria tudo o que está entre as pontas. As duas estruturas se encontram num lugar só: a classe de serviço `Map` (`server/.../Map/001.php`, método `search`) devolve `relationship` e `organization` na mesma resposta, e é dela que sai a lista de "abrir mapa" — por isso o `SELECT` do organograma traz `creation_time`/`modification_time` explícitos, para a lista poder ordenar os dois tipos pela data de edição.

As **regras de conteúdo** de um mapa — caixinha só com o nome, apelido/sigla no `small_label` (que **substitui** o nome no desenho de pessoa/outro), cargo daquele momento como referência datada, vínculo com verbo curto e data nas pontas, descrição da entidade = quem ela é (não o que a matéria diz), fonte só na referência, buscar antes de criar — estão em **`EDITORIAL.md`**. Leia-o antes de escrever script ou bot que grave mapa.

Um mapa também tem **documentos** anexados (hoje só PDFs de report). O `Document` (`app/classlib/document.py`, `server/.../Document/001.php`) grava os bytes **fora do banco**, em `server/data/documents/<sha256>.pdf` (coberto pelo `Deny from all` do `data/.htaccess`); o banco guarda só hash, tamanho e vínculos. O `sha256` é a chave de deduplicação — o mesmo PDF em N mapas grava o arquivo uma vez e cria uma linha em `document_map` por mapa. O servidor confere a assinatura `%PDF-` em vez de confiar na extensão.

Cada entidade também tem **imagens** — ao contrário do `Document`, gravadas **em base64 dentro do banco**. Uma lista (`entity_image`) para qualquer objeto e um **rosto** opcional (`entity_face`, 1 por objeto, exceto vínculo). O cliente **reduz toda imagem** antes de enviar (o usuário autorizou perder qualidade): `png_base64_from_file` (`app/view/ui/qimages.py`) reduz o maior lado a `MAX_LADO` e salva como **JPEG** (qualidade `QUALIDADE`), achatando alpha sobre branco — fotos/screenshots de vários MB viravam base64 gigante. O nome da função é legado ("png_"); os **decodificadores auto-detectam o formato** (JPEG novo ou PNG já gravado), então nada quebra. O transporte é um **endpoint dedicado** `Entity.load_images`/`save_images` (não viaja no save do mapa, para não inchar o `diagram_relationship_history`); o `save_images` faz um upsert **não-destrutivo** da linha em `entity` antes de gravar (a FK de `entity_image`), então imagens funcionam mesmo numa caixa ainda não salva no mapa. O widget `QImages` (embutido nas abas "Images" dos diálogos de entidade e de vínculo) carrega e grava sozinho, na hora de cada alteração. **As tabelas `entity_image`/`entity_face` precisam da migração no banco live** — ver o bloco de migração comentado (junto de `entity_face`) em `server/data/create.sql`.

Entidades **Other** têm um **subtipo** (`sub_etype`, chave = `md5(nome)`). O **cadastro** dos subtipos válidos e o **rosto default** de cada um são **globais** (nível banco), numa tela própria `DialogSubtypes` (`app/view/dialog_subtypes.py`, aberta pelo item "Sub-tipos" no menu File / toolbar) — não ficam dentro da entidade. Dentro do diálogo da Other, na aba **Actions**, há apenas um combo somente-leitura para **selecionar** um subtipo já existente. Cada subtipo pode ter um **rosto default** (`sub_etype.face_default`, base64) compartilhado por todas as Others dele. No mapa (com `show_face`), o `face_default` do subtipo aparece como **badge** — imagem pequena **antes do nome**, na mesma linha (`MapRelationshipBox.draw_subtype_badge`), somado ao que já é exibido. Mas o **rosto próprio tem preferência**: se a entidade tem `entity_face`, o badge do subtipo **não** aparece. O `load` do servidor (`MapRelationship/001.php`) entrega `face` (próprio) e `subtype_face` (do subtipo) **separados**. Endpoints em `Entity/001.php`: `load_subetypes`, `create_subetype`/`delete_subetype` (gerência global), `set_subetype_face` (rosto default do subtipo), `set_subetype` (atribui um subtipo a uma entidade).

Cada mapa (`MapRelationship`) tem duas configurações no diálogo **Property** (`DialogRelationshipEdit`): **Idioma** (`language`, um de `pt-BR`/`en`/`es` — a lista canônica é `report.IDIOMAS`) e **Exibir PNG de rosto** (`show_face`). O idioma alimenta o prompt do **report** e do **bot de entidades** (via `report.idioma_frase`, único ponto de verdade — o report não é mais fixo em português). Com `show_face` ligado, quando a entidade (pessoa/org/outro) tem rosto, a **imagem substitui a caixinha com o nome** — não desenha retângulo nem texto, só o PNG (`MapRelationshipBox.mostra_rosto`/`draw_face_only`; o `recalc` dimensiona `w`/`h` pela miniatura para a área de clique e as linhas de vínculo baterem na imagem). Sem rosto, a caixa normal com o nome. O servidor só traz os `entity_face` no load do mapa quando `show_face` está ligado, e o efeito de ligar aparece **ao reabrir** o mapa (o load atual não tinha os rostos). Ambos os campos persistem em colunas novas de `diagram_relationship` (mesma migração).

O banco de entidades é **semeado com CTI do MISP Galaxy** (github.com/MISP/misp-galaxy): threat actors, malware, ransomware, RATs — ~7.900 entidades no domain `cyberwar`, com sinônimos (`entity_aka`), referências e relações globais (`entity_simple_association`, entidade↔entidade, ainda sem UI). Convenção: entidade **de origem MISP** tem `id` no formato **UUID** (com hífens); entidade **nativa** tem `id` `hex_hex_hex` (underscores) — isso torna a origem identificável e reversível. Colisões de nome **enriquecem** a entidade existente (não duplicam). Mapeamento, reexecução e rollback em **`docs/MISP-GALAXY.md`**; o importador é `script/misp_import.py`. Um segundo seeder, `script/country_seed.py`, cadastra **países** (galaxy `country` do MISP) como Others com a **bandeira** (flagcdn PNG) de rosto (`entity_face`); `id` = `uuid5` do ISO (formato UUID, reversível como o import MISP), enriquece por nome, idempotente, e lê as credenciais do banco de `~/.env` (`{PROJETO}_DB_HOST_REMOTO/_USER/_PASSWORD/_DATABASE`). Roda com `--country <clusters/country.json>` (dry-run) mais `--write` para gravar; requer `pymysql` e `requests`. Panorama de infra e fontes de dados em **`docs/ARQUITETURA.md`**.

Fora dos seeders (que falam MySQL direto), a carga em massa pela via normal do app é o `DialogImport` (`app/view/dialog_import.py` + `app/classlib/importlib.py`): cada arquivo escolhido é **um** JSON de uma entidade e precisa trazer **todas** as colunas `text_label`, `small_label`, `description`, `etype`, `sub_etype`, `wikipedia`, `default_url`, `icon` — se faltar uma, o lote inteiro é abortado. O servidor grava tudo numa tacada em `Entity.import_all`.

### Timeline — o terceiro tipo de diagrama

A `Timeline` (`app/classlib/timeline/`) é um **documento**, como o mapa e o organograma: tem nome e keyword, é criada pelo **New**, salva, aparece na lista do **Open** (o `Map.search` devolve os três tipos) e pertence a um usuário. O que ela **não** guarda é geometria — a posição de um evento *é* a data dele, então não há x/y para persistir. Tabelas: `diagram_timeline` e `diagram_timeline_event`.

O **mapa de origem é opcional** (`diagram_timeline.diagram_relationship_id`), e é ele que define os dois modos:

- **com mapa** — a timeline **projeta** as datas que já estavam lá e soma os eventos marcados;
- **sem mapa** — timeline solta, só com os eventos que o analista marcar.

São **seis origens de data**, cinco de projeção e uma marcada à mão (`timeline_event.py` guarda o mapa de cor/rótulo/prioridade; a legenda sai daí para não discordar do desenho):

| Origem | De onde vem |
|---|---|
| Evento marcado | `diagram_timeline_event` — o único que a timeline cria |
| Acontecimento | `diagram_relationship_element_reference.start_date/end_date` |
| Vínculo | `diagram_relationship_link` (um evento por **ponta datada**: as duas pontas podem ter períodos diferentes) |
| Classificação | `entity_classification_item` |
| Entidade | `entity.start_date/end_date` |
| Caixa no mapa | `diagram_relationship_element.start_date/end_date` |

A projeção é feita **no cliente**: o `Timeline.load_data` carrega o mapa pelo caminho normal (`MapRelationship.load`, que já traz todas as datas) e varre o que veio. O servidor não relê o mapa — duplicar essa leitura criaria uma segunda verdade sobre o que conta como data.

Regras do desenho: data única vira **marco** (abaixo do eixo), período vira **barra** (acima); eventos que disputam o mesmo trecho do eixo **sobem de nível** em vez de escrever um por cima do outro; eventos idênticos (mesmo título e mesmas datas) são **deduplicados** ficando a origem de maior prioridade — a data da entidade costuma estar repetida na caixa do mapa. Data suja (`0000-00-00`, `NULL`, texto) simplesmente não vira evento, e período invertido é normalizado: um mapa mal cadastrado não pode derrubar o desenho inteiro.

O **layout mora no modelo** (`timeline.py`: escala, ticks, empilhamento, `draw`), como no organograma; `app/view/ui/mapa_timeline_engine.py` só cuida de mouse, pixmap e menu. Como a largura é o zoom do eixo (pode passar de dez mil px), a timeline é embrulhada num `QScrollArea` no `MdiMap` (o mapa de vínculos não precisa: virou `QGraphicsView`, que já rola e dá zoom sozinho; o organograma é o único ainda sem rolagem). Não há arrastar elemento; o que se ajusta é o zoom (Ctrl+roda ou menu) — a roda **sem** Ctrl é encaminhada à mão para a viewport da área (rolagem vertical/horizontal), porque a propagação automática do wheel não é garantida. O passo vertical de cada faixa empilhada é **medido na fonte** (`Timeline.__passos__`), não fixo: com constante fixa o rótulo encavalava na faixa de cima assim que a fonte do mapa crescia.

**Referência com data = acontecimento.** A referência já era a fonte ("o que diz que isso aconteceu"); com data ela vira também o fato datado. Continua opcional — sem data, segue sendo só fonte. O campo está no `DialogReference` (aba Referencia) e a data aparece na coluna "Acontecimento" das abas References. Grava no **save do mapa**, junto do resto da referência.

**Evento marcado** (`MapEvent`, `app/classlib/timeline/map_event.py`) é o acontecimento que não está em nenhum outro cadastro. Pertence à **timeline**, não ao mapa (a mesma investigação pode ter várias linhas do tempo com recortes diferentes), tem entidade associada **opcional** e grava **na hora** por endpoint próprio (`TimelineEvent/001.php`, `save`/`delete`) — não pelo save do documento, que teria de mandar a lista inteira de volta a cada evento novo. Botão direito na timeline: novo/editar/remover. Projeção não se edita ali: a data mora no vínculo/classificação/referência e é lá que se muda.

**Migração obrigatória** para bancos que já existem (o deploy não altera banco; ver `DEPLOY.md`): as três colunas de data em `diagram_relationship_element_reference` e as tabelas `diagram_timeline`/`diagram_timeline_event`. O bloco pronto está no fim de `server/data/create.sql`. Sem ela, o load do mapa quebra — o `SELECT` das referências nomeia as colunas novas.

Um cuidado que vale para todo o modelo: **toda ponta de data tem que sobreviver ao load**. O `Link.addFrom` descartava as datas que o servidor mandava, e o save seguinte gravava `NULL` por cima; o mesmo valia para as referências carregadas pelo `Entity.load` e para as copiadas pelo `incorporate`. Ao mexer em qualquer caminho de carga, confira se as três colunas (`start_date`/`end_date`/`format_date`) chegam ao objeto.

O par de datas na interface é o widget `QPeriodo` (`app/view/ui/qperiodo.py`): dois `QDateEdit` com botão Enable/Disable — "sem data" é um valor legítimo, diferente de "hoje" — mais o combo de formato. O `DialogLinkEdit` e o `DialogClassification` têm a mesma UI escrita à mão, de antes do widget.

### Lei do projeto: SVG só o que a gente gera

**O risco é SVG de procedência desconhecida, não o formato** (decisão do dono, 2026-10-05, depois
de eu ter generalizado para um banimento que estava errado). SVG é XML que pode carregar
`<script>`, `<foreignObject>`, `xlink:href` remoto e expansão de entidade — mas o que o
`QSvgGenerator` produz da nossa própria cena só tem `path`/`text`/`rect`. A linha fica assim:

- **Export para arquivo local: PDF (`QPdfWriter`), PNG e SVG (`QSvgGenerator`).** SVG pode.
- **`Document` anexado, que o app web serve: só PDF e PNG.** O diretório de `Document` não pode
  virar endpoint que serve `image/svg+xml` — um SVG **de upload** cairia no mesmo lugar e
  executaria na origem do CML (XSS armazenado). A validação é por **bytes mágicos**, não por
  extensão, como o `%PDF-` que o `Document` já confere.
- **Imagem de entidade (`entity_image`/`entity_face`): só raster.** Este é o caso literal de
  upload de SVG. Já está seguro e deve continuar: o data URI do canvas JS tem MIME de **lista
  fixa** (`server/webpage/view/relationship/relationship.php:156`) — jpeg ou png, **nunca**
  `image/svg+xml`. Ponta a endurecer: `QPixmap.loadFromData` detecta formato pelo conteúdo, então
  conferir bytes mágicos antes (ver `SPEC.md` §3.5).

### Reports em segundo plano (rolhama)

> ⚠️ **O `rolhama` caiu em 2026-10-05 e, por decisão do dono, não volta.** Tudo nesta seção —
> mais o bot `entidades` e o transform `ia.extrair` — está **parado**: o código fica no disco,
> mas o caminho não funciona em runtime. O que cada ponto deve anunciar como indisponível (em
> vez de estourar exceção) está em **`SPEC.md` §8**, junto do backend que substitui o rolhama
> (Ollama local pelo app + OpenCode/MCP para trabalho conduzido). Documento de report já gerado continua abrindo e baixando.
> A descrição abaixo vale como registro de como o caminho funciona.

Um mapa gera um **relatório em PDF** a partir das suas fontes: `app/classlib/report.py` coleta os links das entidades — os da aba References **mais o site oficial (`default_url`) e a Wikipedia (`wikipedia`)** de cada entidade, quando forem URLs http(s), deduplicados —, baixa o texto (até `MAX_REFERENCIAS = 50`, o resto vai listado em "Demais referências"), monta **um único prompt** e manda ao LLM; a saída vira PDF via `QTextDocument`→`QPdfWriter` e é anexada como `Document`.

O **idioma** do mapa (`language`, default `en`; ver *Modelo de domínio*) vai em **toda** chamada ao rolhama e é **reforçado no output**: `report.instrucao_idioma(codigo)` devolve uma instrução forte no próprio idioma-alvo e `Rolhama.gerar(..., idioma_instrucao=...)` a anexa como **última linha** do prompt (recência). Report e bot de entidades passam isso; "linguagem natural" na instrução exclui de propósito as chaves JSON do bot.

- **Um prompt só, não um por referência**, porque o worker do rolhama serializa **globalmente** (uma geração por vez em toda a máquina); cada chamada segura a fila de todos os projetos. O corte de referências existe para caber na **janela de contexto do modelo** — se estourar, o ollama trunca o prompt em silêncio e o modelo responde confiante sobre o pedaço que viu, então `report.py` derruba referências até caber e diz quantas.
- A geração roda no `ReportManager` (`app/view/ui/report_manager.py`), um **singleton de módulo** que vive fora dos diálogos: a `QThread` não pertence ao `DialogDocument`, senão fechar a janela mataria a geração. A GUI só escuta sinais (`progresso`/`concluiu`/`falhou`/`mudou`); a janela principal mostra o estado no botão "Documents".
- A trava entre máquinas é o `ReportJob` (`server/.../ReportJob/001.php`): uma coluna gerada `lock_global` com índice `UNIQUE` garante **um report por vez no domain** sem "verifica e insere" (que teria corrida). Jobs cujo dono sumiu por mais de 45 min são expirados antes de cada aquisição. `ReportManager` também tem uma trava local, que só impede disparar dois no mesmo cliente.

**O cliente do rolhama fala o contrato webapi** (migrado do bddphp antigo, que foi apagado da Hostinger). `app/classlib/rolhama.py` usa `webapi.ClientAPI` (`app/classlib/webapi.py`, cópia literal de `../rolhama/llm/webapi.py`): `enqueue`/`response` por **job UUID**, MAC de autenticação (`K_auth[canal]`), sem 409 nem `remove()`, teto de 64 MiB. A cifra do payload é ChaCha20-Poly1305 por `(part, canal)` via `bdd.seal`/`bdd.open_blob` (o `app/classlib/bdd.py` é **byte a byte idêntico** ao do worker — se divergir, a resposta não decifra). URL vem de `ROLHAMA_WEBAPI_URL` (aceita `ROLHAMA_BDD_URL` por compat), chave de `ROLHAMA_BDD_KEY`, ambas do `~/.env`.

O webapi ainda **não tem rota de alocação** de canal (é pendência do lado rolhama — `../rolhama/llm/CANAIS.md`), então o canal é **fixo por projeto**, semeado no servidor e mapeado em `CANAL_POR_PROJETO`: report (`"cml"`) → **507**, bot de entidades (`"cml/entidades"`) → **510**, sobrescrevíveis por env (`CML_ROLHAMA_CANAL`, `CML_ROLHAMA_CANAL_ENTIDADES`). Projetos diferentes precisam de canais diferentes porque a mesma chave decifraria a resposta um do outro. O `Rolhama.alocar()` sobreviveu só como compat — hoje devolve o canal fixo, sem ir ao servidor. Contrato completo em `../rolhama/llm/INTEGRACAO.md`; para atualizar o transporte, recopie `webapi.py` e `bdd.py` de `../rolhama/llm/`.

**A confirmar do lado do servidor:** que os canais 507/510 estejam semeados e sendo atendidos pelo worker (o `CANAIS.md` os lista na faixa da semente 500–510, mas marcados "livres" — o CML não aparece na tabela de consumidores).

**A "máquina 90" (o host do rolhama/ollama):** GPU **RTX 5060 16 GB**. Modelo default `qwen2.5:14b-instruct-q6_K` (`report.py`, sobrescrevível por `CML_REPORT_MODELO`; usado por report **e** bot de entidades) — q6_K + 16k de contexto ≈ ~15 GB, encaixa justo na 16 GB; se der OOM, baixar `ROLHAMA_OLLAMA_NUM_CTX` (12288/8192) no `~/.env` **da máquina 90** ou voltar ao Q4. O worker **serializa globalmente** (uma geração por vez na máquina), por isso o report manda um prompt só. Panorama de infra e fontes de dados em `docs/ARQUITETURA.md`.

### Transforms (estilo Maltego) — `app/transform/`

Botão direito numa caixa do mapa de vínculos → submenu **Transforms** (agrupado por fonte; os
indisponíveis ficam visíveis com o motivo). Um transform é `(entidade) → entidades + vínculos`;
o resultado **nunca grava direto**: abre o painel **Proposta** (`view/dialog_transform_proposta.py`),
onde o analista marca, confere o tipo e escolhe *criar nova* ou *reaproveitar* a entidade que já
está na base (busca antes de criar). Só então `transform/aplicar.py` insere no modelo, em círculo
ao redor da caixa de origem; persistir é o save do mapa, como sempre. Contrato e decisões em
**`SPEC.md`**; catálogo de fontes OSINT em `docs/OSINT.md`; servidor MCP em `docs/MCP.md`.

- **Núcleo sem Qt** (`nucleo.py` registro/executor/`Resultado`; `contexto.py` HTTP, LLM, craudiowebot,
  base) — testável com `python3` puro; a casca Qt é `view/ui/transform_manager.py` (singleton de
  módulo com `QThread`, como o `ReportManager`) + o painel. **Os sinais do worker ligam em slots
  do gerente, não em lambdas**: lambda sem objeto de contexto roda na thread do emissor e o
  `thread.wait()` espera por si mesmo (deadlock).
- `app/transform/_osint.py` guarda os ajudantes compartilhados pelos conectores de `api_aberta/`
  (achar o alvo — domínio/IP/ASN/CNPJ/CEP/e-mail — no `text_label`/`small_label`/`description`/`default_url`,
  repetir requisição que falhou por instabilidade da fonte, cortar texto). Conector novo de OSINT
  reusa dali em vez de reescrever o reconhecimento do alvo.
- **Transform novo** = pasta `app/transform/<fonte>/<nome>/` com `config.json` (`id`, `nome`,
  `entrada` como `etype` ou `etype:sub_etype`, `fonte` ∈ base-propria|api-aberta|ia|scraping,
  `rota`, `chave_env`, `ttl` do cache em segundos) e `transform.py` com subclasse de
  `nucleo.Transform`. O `Registro` relê a cada menu: não precisa reiniciar. O `Resultado` é
  validado pelo `Executor` depois de **todo** transform (limites, ponta solta, sem referência → aviso).
- **Toda informação traz fonte**: `ctx.ref(título, url)`. A data de **coleta** vai na *descrição*
  da referência, nunca em `start_date` — referência com data vira acontecimento na timeline.
- **Rede**: `ctx.http()` sai com UA de Firefox corrente (`transform/contexto.py:UA`; atualizar a
  cada uso, regra do dono) e pela rota do transform: `direta` ou `tor` (SOCKS5 `socks5h`, o DNS
  também sai pelo Tor — por isso DNS é via DoH, nunca resolvedor local). Rota padrão: `CML_TX_ROTA_PADRAO`.
- **LLM** via `ctx.llm()`: `rolhama` (padrão, canal **510**) ou `ollama` direto (opt-in:
  `CML_LLM_BACKEND=ollama` + `CML_OLLAMA_URL`). Desde **2026-10-05** o Ollama local é o caminho
  **normal**, não exceção: a lei do `workspace/CLAUDE.md` foi reescrita ("LLM é local e sob
  demanda") porque o `rolhama` custava manter ligado. O `rolhama` como backend não existe mais.
- **Cache e log são locais**: `~/.cml_cache/` (0700/0600). `transform.log` é a única trilha de
  auditoria — a execução é no cliente, nada vai ao servidor.
- `base.associadas` usa o método novo `Entity.associations` do servidor: **precisa de deploy**
  (flag-portão do `DEPLOY.md`); sem ele o transform diz que o servidor não o conhece.
- Teste headless: `QT_QPA_PLATFORM=offscreen` com um transform falso apontado por `_dir` no `cfg`
  (o `Executor` aceita `cfg` solto; `HOME` apontado para um diretório temporário isola cache/log).

### App web (somente leitura)

`server/webpage/` é um app PHP MVC próprio (não JSON-RPC) para **visualizar** mapas e baixar documentos pelo navegador. Entra por `server/webpage/index.php`, que escolhe o domain (reusa `Mysql::domains()` do `data/config.json`) e redireciona para a lista. É servido no caminho `.../cml/webpage/`. Estrutura clássica `controller/`/`model/`/`view/`/`service/`, com os assets em `public/`.

O canvas JS do mapa (`view/relationship/relationship.php`) **desenha os rostos** quando o mapa está com `show_face`: o rosto próprio (`entity_face`) substitui a caixa e o rosto default do subtipo (`sub_etype.face_default`) vira badge (o próprio tem preferência). O modelo (`model/relationship/`) só carrega os base64 quando `show_face` está ligado. As imagens vão como data URI que auto-detecta JPEG/PNG. As **"Relações"** (lista textual) ficam em **aba própria**, separadas do mapa. Abas: Mapa · Relações · Documentos · Referências.

### Os bots são plug-ins

Os bots ficam em `app/bot/<pais>/<nome>/`, cada um um `config.json` mais um módulo. Hoje existem quatro em `app/bot/brazil/`: `wikipedia` (scrape), `wayback` (gravação no Wayback), `referencias` (busca links candidatos para uma entidade via Wikipedia/DuckDuckGo) e `entidades` (extrai sujeitos e vínculos de uma URL pelo rolhama, com `format=json`, num canal/projeto próprio — `Rolhama(projeto="cml/entidades")` — separado do canal do report). O `config.json`:

```json
{"button": "Load", "path": "bot/brazil/wikipedia/search.py", "class": "DialogBotWikipedia", "module": "dialogbotwikipedia"}
```

O `app/view/ui/qbot.py` renderiza o botão e carrega a classe no momento do clique, via `importlib.util.spec_from_file_location`, instanciando como `cls(parent, obj)`, em que `obj` é a entity ou a reference que está sendo editada. Para adicionar um bot: crie o diretório e depois coloque um widget `QBot(self, <obj>, "bot/.../config.json")` em um diálogo (veja `dialog_entity_generic.py` e `dialogreference.py`).

### Importar é proposta, nunca gravação

`app/classlib/importar_dados.py` lê CSV e GraphML para um **`Resultado`** — a mesma estrutura que
um transform devolve — e entrega ao painel **Proposta**. Isso não é rodeio: é o único jeito de
importar sem furar duas regras ao mesmo tempo, "entidade é global" e "curadoria humana". Um
importador próprio criaria uma entidade nova por linha da planilha, e 300 linhas virariam 300
duplicatas para o `merge_to` limpar depois. As colunas são reconhecidas por **nome** (várias
grafias, pt e en), o delimitador (`;` ou `,`) é detectado, e planilha só de vínculos cria também
as entidades das pontas. Para isso o `transform/aplicar.py` passou a aceitar **origem `None`**:
sem caixa de origem o círculo nasce no centro do que já está desenhado, e vínculo que cite
`ENTRADA` simplesmente não é criado.

### Colapsar grupo (collection)

É **vista**, como o ocultar: o documento não sabe que existe grupo, nada entra no desfazer, nada é
salvo. O `ItemGrupo` não é um element — é só desenho. Duas coisas que parecem detalhe e não são:
ele **redesenha os vínculos que atravessam a fronteira** do grupo (sem isso o grupo aparece
desligado do resto, e quem olha conclui que aquelas caixas não se ligam a nada), juntando numa
linha só os que vão para o mesmo alvo pelo mesmo verbo, com a contagem; e a caixa do grupo
**foge de quem ficou na tela** antes de se posicionar — o centro dos membros parece o lugar óbvio,
mas numa topologia de estrela é exatamente onde está o hub, e como o grupo tem `zValue` maior ele
engoliria a caixa mais importante do mapa.

### Copiar/colar: a entidade é global, a caixa não

`app/classlib/relationship/transferencia.py` (Ctrl+C/Ctrl+V). O pedaço de mapa viaja como **texto
JSON** na área de transferência do sistema, com cabeçalho `CML-MAPA-1` — assim funciona entre
janelas e entre duas execuções do CML, e colar texto de qualquer outra origem é recusado sem
susto. A regra que manda: **colar não duplica a entidade**, cria uma **caixa** nova apontando
para o **mesmo `entity_id`**. Duplicar a entidade criaria um gêmeo que o `merge_to` teria de
juntar depois. Por isso colar o mesmo pedaço no mesmo mapa gera duas caixas da mesma entidade, e
isso é legítimo. Vínculo só viaja se **as duas pontas** estiverem na seleção — meia aresta colada
viraria ponta solta no destino.

### Minimapa

`app/view/ui/minimapa.py`: um segundo `QGraphicsView` sobre **a mesma `QGraphicsScene`** do
canvas. Clonar os itens daria duas verdades sobre o desenho e obrigaria a aplicar cada mudança
nos dois. Ele é `setInteractive(False)` — clicar ali é "me leve até lá", nunca "selecione" — e
marca o visível **escurecendo o que está fora**, porque num mapa grande um contorno fino some. A
borda usa caneta de largura 0 (um pixel de tela, sem escalar junto com a miniatura reduzida).

### Exportar: figura e dado são dois caminhos

`app/classlib/exportar_diagrama.py` tira a **figura** (PDF/PNG/SVG, os três diagramas);
`app/classlib/exportar_dados.py` tira a **informação** (CSV e GraphML, só o mapa de vínculos).
Três decisões que não são óbvias: **CSV são dois arquivos** (entidades e vínculos), porque as
colunas de um não são as do outro — mesma razão das duas abas da List View; a **hiper-aresta vira
uma linha por par**, já que nem planilha nem GraphML sabem o que é aresta de várias pontas, e
cada par ganha o id do vínculo com sufixo; e o `grau` do export conta **arestas expandidas**, não
vínculos — se contasse vínculos, o nó diria "2" num arquivo onde o Gephi vê 3 arestas. A coluna
*Vínculos* da List View conta outra coisa de propósito (quantos vínculos tocam a caixa), porque no
mapa o vínculo é **um** objeto. CSV sai em `utf-8-sig`: sem o BOM o Excel abre a acentuação errada.

### Viewlets e ocultar: as duas coisas que mudam a vista, não o documento

**Viewlets** (`app/classlib/relationship/viewlets.py`, botão **Vista**) são um mecanismo, não uma
regra fixa: cada um devolve, por caixa, `(escala, cor)`. Daí saem tamanho por vínculos, por
*entity rank* (os próprios mais a soma dos vizinhos), por referências, cor por tipo e
**cor: sem fonte** — a regra do `EDITORIAL.md` virando cor. Dois cuidados no canvas: a cor é
pintada como **moldura atrás** da caixa (o `draw` de cada tipo já preenche o próprio retângulo de
branco ou amarelo, então pintar por cima não adiantaria), e a ampliação é aplicada **também ao
`shape()`** — desenhar com transform e esquecer o hit test faz a caixa crescer e continuar
recebendo clique no tamanho antigo.

**Ocultar sem apagar** é estado de vista: fica em `engine.ocultos`, **não entra no desfazer** e
não é salvo. Três regras: ocultar uma caixa esconde também os vínculos que a tocam (senão a
linha vai até uma caixa fora da tela); `getElement` só enxerga o visível, para não pegar caixa
"no escuro"; e a **busca revela** o que estiver oculto, porque achar sem mostrar faria o analista
concluir que a caixa não existe.

### Seleção, busca e apagar em massa no canvas

Laço com o **botão esquerdo** no vazio (`RubberBandDrag`), Shift soma à seleção, e arrastar
qualquer caixa selecionada move **o grupo inteiro** em um passo de desfazer. Clicar numa caixa
*fora* da seleção recomeça a seleção nela — senão arrastar uma caixa qualquer sairia levando
junto um grupo que o analista não lembra ter feito. Por causa do laço, **arrastar a tela passou
para o botão do meio** (mais as barras de rolagem e a roda). Ctrl+F busca por nome, apelido ou
sub-tipo, seleciona os achados e centraliza no primeiro.

`apagar_selecionados()` vai em **ordem de dependência dentro da seleção**: os vínculos escolhidos
perdem as pontas e saem primeiro, depois as caixas que nenhum vínculo restante referencia. Caixa
presa a um vínculo que ficou **fora** da seleção é barrada e contada, nunca apagada por tabela —
a cascata é explícita e limitada ao que o analista marcou.

> ⚠️ **Defeito corrigido em 2026-10-05, achado pelo teste:** a guarda do `MapRelationship.delEntity`
> comparava `buffer_ref.entity.id == element.entity.id`. O lado esquerdo é o id da **caixa**
> (`LinkEntity.entity` *é* o element) e o direito o id da **`Entity`** de dentro dela — espaços de
> id diferentes, que nunca batiam. A guarda documentada ("apagar caixa em vínculo lança exceção
> em vez de fazer cascata") **nunca disparou**: a caixa saía calada e o vínculo ficava apontando
> para algo fora do mapa, desenhando linha para o nada e salvando ponta solta. Agora compara com
> `element.id`.

### Desfazer/refazer: a pilha mora no documento

`app/classlib/relationship/comandos.py`. O mapa é mexido em **cinco** lugares bem diferentes
(arrastar no canvas, criar pelo duplo clique, apagar por `dialog_entity_generic`/`dialogentitylink`,
`incorporate`, e o `transform/aplicar.py`), então em vez de um comando com inverso por operação
— cinco chances de errar, e o inverso do `incorporate` é o pior deles — há **um instantâneo** de
**estrutura e posição**: quais elements estão no mapa e em que ordem, o `x`/`y` de cada um, e as
duas listas de ponta de cada vínculo (que é o que o `incorporate` reaponta). Nada é clonado: os
objetos seguem os mesmos, então diálogo aberto e referência guardada por aí não viram ponteiro
para lixo depois de um desfazer, e `mapa.elements` continua sendo **a mesma lista** (a reposição
é por fatia, `elements[:] = ...`).

Quem mexe no mapa envolve a mutação em `with Operacao(mapa, "Apagar caixa"):` — e só empilha se
algo mudou de fato, nada se a operação estourar no meio. A pilha é `mapa.desfazer`
(`QUndoStack`) e mora no **documento**, não na janela: toda rotina que muda o mapa já tem o mapa
em mãos, e nenhuma precisa saber qual janela está aberta. O `MdiMap` só escuta `indexChanged`
para redesenhar. **O que ele não desfaz, de propósito:** edição *dentro* de um objeto (nome,
descrição, referência, data) — isso tem Cancelar no próprio diálogo, e guardar aqui exigiria
clonar entidade inteira a cada clique.

### Layouts automáticos

`app/classlib/relationship/layouts.py`, os cinco do Maltego (orgânico, hierárquico, circular,
bloco, ortogonal) mais o **Espalhar**, sem biblioteca externa.

O **Espalhar** é o único com promessa forte: **zero colisão** (contando as caixinhas de verbo) e
**aresta apontando para baixo**. Como mapa é grafo e grafo tem ciclo, uma busca em profundidade
marca as **arestas de retorno** e as tira da conta das camadas — elas saem apontando para cima, e
isso é proposital: inventar hierarquia onde não há seria pior que mostrar o ciclo. Depois vêm
camadas por caminho mais longo e ordenação por baricentro (reduz cruzamento).

O posicionamento horizontal é em **cascata**, não por camada centralizada: o `x` nasce da família
— filho sob a média dos pais, pai sobre a média dos filhos — com passadas alternando de cima para
baixo e de baixo para cima até assentar. A primeira versão centralizava cada camada em zero e o
resultado era uma pirâmide amontoada no meio, aceitável num mapa de brinquedo e ilegível num
real. Depois de **cada** ajuste a camada é varrida da esquerda para a direita empurrando quem
encostou, e é isso que faz "o mais próximo possível" nunca virar sobreposição. Caixa **sem
vínculo nenhum** não entra na cascata (ela não desce de lugar algum): vai para uma **prateleira**
embaixo, empacotada — deixá-la na primeira camada abria um vão enorme, porque ela ficava na
origem enquanto a árvore se afastava para a direita durante o assentamento. Só nele a caixinha do verbo também é afastada (`afastar_vinculos`), e só a caixa do
**verbo** se mexe: mover entidade ali desfaria o trabalho do algoritmo.

**O texto do vínculo entra na briga da colisão como qualquer caixa** — e é ele quem mais se
sobrepõe, porque vários vínculos entre as mesmas duas caixas têm o **mesmo ponto médio** e os
rótulos nascem todos empilhados. A busca é em **anéis** a partir do ponto certo, com passo do
tamanho do próprio rótulo, preferindo subir/descer (onde há folga entre camadas) antes de ir para
os lados; os mais largos são colocados primeiro, enquanto ainda há espaço.

> ⚠️ **Ao testar colisão, chame `recalc(painter)` antes de medir.** O `w`/`h` de uma caixa só vale
> depois dele — sem painter, todas ficam com a largura padrão, o teste mede caixas de mentira e
> passa. Foi exatamente o que escondeu o defeito dos rótulos empilhados até o mapa real mostrá-lo
> na tela. São **ação, não modo**: rodam uma vez, escrevem `x`/`y`
e saem. Três coisas a não quebrar: cada layout entra como **um** passo de desfazer (sem isso o
botão seria destrutivo, porque joga fora posicionamento manual); o **vínculo não participa** — é
hiper-aresta, e a caixa do verbo vai para o meio das pontas *depois* que as caixas acharam lugar;
e tudo é normalizado para coordenada **positiva** no fim, porque o modelo e o banco nunca
trabalharam com `x`/`y` negativo. O orgânico tem **semente fixa**: mesmo mapa, mesmo desenho.

### A List View — o mapa em tabela

O mapa de vínculos tem **duas vistas na mesma janela**: o desenho e uma **tabela**
(`app/view/ui/lista_diagrama.py`, botão **Lista** na barra Map). O `MdiMap` guarda as duas num
`QStackedWidget` — alternar não fecha nada. É **vista, não documento**: lê os mesmos `elements`,
não guarda cópia e não grava; quem edita é o diálogo que o duplo clique abre, igual ao duplo
clique no canvas.

São duas abas porque **o vínculo também é element** e as colunas dele são outras: *Entidades*
(tipo·subtipo, nome, apelido, grau, período da caixa, refs, classificações, descrição) e
*Vínculos* (verbo, de, para, e um **período por ponta**). Três detalhes que são armadilha se
alguém mexer: as colunas de número guardam **número** no `DisplayRole` (com texto, "10" ordena
antes de "9"); o índice do element vai no `Qt.UserRole` da primeira célula, porque **com a tabela
ordenada o número da linha não é o índice no modelo**; e o `setSortingEnabled` é desligado
durante o preenchimento, senão as linhas se embaralham enquanto entram.

### Shell da interface

O `application.py` executa o `DialogConnect` **antes** de criar a janela principal e encerra a menos que o `Server.status` esteja setado. A janela principal é um `QMdiArea` cujos filhos são instâncias de `MdiMap`; os menus e toolbars são construídos, mas várias ações estão comentadas. Os diálogos ficam em `app/view/`, como `dialog_*.py`, e os widgets reutilizáveis em `app/view/ui/`.

O `DialogRelationshipCheck` é o *lint* do mapa: mostra `mapa.getErros()` como **Errors** e `mapa.getWarnings()` como **Warnings**, com duplo clique abrindo o diálogo do objeto culpado. O catálogo de regras são os métodos estáticos de `app/classlib/relationship/relationship_info.py` (classe `RelatinshipInfo`, **com o typo no nome** — buscar por "Relationship" não acha) — regra nova é um método estático a mais ali, chamado de dentro do `getErros`/`getWarnings` do mapa.
