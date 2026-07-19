# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é isto

O CML é uma ferramenta de análise de vínculos dividida em duas partes: um **cliente desktop PySide6** (`app/`), que desenha mapas de relacionamento e organogramas, conversando com um **servidor PHP + MySQL** (`server/`) através de um endpoint JSON-RPC próprio. O código, os comentários e as mensagens de interface estão majoritariamente em português (pt-BR); mantenha essa convenção ao editar os arquivos existentes.

## Comandos

Não há build system, runner de testes, linter nem `requirements.txt`. As dependências são instaladas de forma imperativa.

```bash
# Instala as dependências do cliente (a lista está em app/install.sh)
pip3 install requests PySide6 pycryptodome pyspellchecker beautifulsoup4 waybackpy

# Executa o cliente (mostra o diálogo de Connect/Login primeiro; encerra se o login falhar)
python3 app/application.py

# Empacota o servidor + o tarball do cliente em /tmp/server (precisa ser executado de dentro de script/)
cd script && ./deploy.sh
```

O `app/install.sh` é o instalador para o **usuário final**, não um comando de desenvolvimento: exige root, recebe a URL do site, baixa o `client.tar.gz` desse site, descompacta em `/opt/cml` e cria o symlink `/bin/cml`.

O procedimento completo de publicação em produção (Hostinger/LiteSpeed, a flag-portão do deploy, o `data/` que nunca é enviado) está em `DEPLOY.md` — leia-o antes de mexer no `deploy.sh` ou em qualquer coisa de deploy.

Os recursos de report e o bot de entidades falam com um serviço externo (o **rolhama**) e leem segredos do `~/.env` (`ROLHAMA_BDD_KEY`, `ROLHAMA_WEBAPI_URL`/`ROLHAMA_BDD_URL`, etc.). Nada de valor concreto vai em arquivo versionado — sempre a variável, nunca o valor. Sem essas variáveis, o report simplesmente falha em runtime; o resto do app funciona.

Para subir o servidor: Apache + PHP com o diretório `server/` servido no caminho **`/cml`** da raiz web (o cliente tem `/cml/services/execute.php` fixo no código), o schema MySQL de `server/data/create.sql` e um diretório de certificados com permissão de escrita (`/var/certs/`, conforme `server/data/config.json`), onde o par de chaves RSA é gerado na primeira requisição.

### Testes

Não existe framework de testes. `app/test/user.py` e `app/bot/brazil/wikipedia/test.py` são scripts pontuais, executados direto com `python3`. Atenção: `app/bot/brazil/wikipedia/test.py` tem um caminho `/home/well/...` fixo no código, que precisa ser editado antes de rodar.

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

### Federação

Um servidor CML pode consultar *outros* servidores CML. O `federation_proxy.php` (chamado pelo cliente via `ConnectObject.__proxy__`) distribui o mesmo envelope para cada servidor federado listado para o domain; o `federation.php` é o endpoint que recebe do outro lado e valida o par `Class.method` contra uma lista de permissões antes de despachar. O `Entity.search(..., proxy=True)` mescla os resultados locais e federados, marcando cada um com um campo `server`. As chamadas de federação não são autenticadas — o acesso é controlado apenas pela chave `federation_id` e pela lista de métodos permitidos no config.

### Autenticação e sessão

Handshake de três etapas em `app/classlib/user.py` + `server/services/classlib/session.php`: o `publickey()` devolve a chave pública RSA do servidor **e o salt do usuário**; o cliente calcula `sha256(password + salt)` e envia para o `login()`, que retorna um token de sessão. O token fica guardado no singleton `Server` e é anexado a todos os envelopes seguintes; o `execute.php` resolve esse token de volta para um usuário via `person_sesion` antes de despachar.

### Singletons e configuração do cliente

`Server` (`classlib/server.py`) e `Configuration` (`classlib/configuration.py`) usam `SingletonMeta` e são acessados por `.instancia()`. O `Server.ip` guarda a **URL base completa** (ex.: `http://localhost`), não um IP, apesar do nome. O `Configuration` persiste em `~/.cml.json`, com os padrões preenchidos pelo helper de caminho pontuado `__getParameter__`.

Todo módulo prepara o `sys.path` com `CURRENTDIR`/`ROOT` via `inspect.getfile` antes dos imports — é por isso que os imports são absolutos (`from classlib.x import Y`) e o app roda a partir de qualquer diretório. Mantenha esse preâmbulo ao criar módulos novos.

### Modelo de domínio

A `Entity` é o registro central (`app/classlib/entity.py`, `server/.../Entity/001.php`), com um `etype` que pode ser `person`, `organization`, `other` ou `link`. As entidades são globais e compartilhadas entre os mapas; o `merge_to` faz a deduplicação repontando todas as tabelas que as referenciam.

Um `MapRelationship` contém `elements`, que são caixas envolvendo entidades. **Os links também são elements**, com `etype == "link"`, carregando as listas `to_entity`/`from_entity` — por isso apagar uma caixa que participa de um link lança exceção em vez de fazer cascata. Os mapas são salvos como documento inteiro: o `save()` serializa o mapa mais o `toJson()` de cada element em uma única chamada. Os mapas também têm trava consultiva (`lock_map`/`unlock_map`); um mapa travado fica somente leitura e o título da janela principal indica isso.

O `OrganizationChart` é a estrutura paralela para organogramas, com seu próprio engine de canvas. Os dois canvas ficam em `app/view/ui/mapa_relationship_engine.py` e `app/view/ui/mapa_organization_chart_engine.py`.

Um mapa também tem **documentos** anexados (hoje só PDFs de report). O `Document` (`app/classlib/document.py`, `server/.../Document/001.php`) grava os bytes **fora do banco**, em `server/data/documents/<sha256>.pdf` (coberto pelo `Deny from all` do `data/.htaccess`); o banco guarda só hash, tamanho e vínculos. O `sha256` é a chave de deduplicação — o mesmo PDF em N mapas grava o arquivo uma vez e cria uma linha em `document_map` por mapa. O servidor confere a assinatura `%PDF-` em vez de confiar na extensão.

Cada entidade também tem **imagens** — ao contrário do `Document`, gravadas **em base64 dentro do banco**. Uma lista (`entity_image`) para qualquer objeto e um **rosto** opcional (`entity_face`, 1 por objeto, exceto vínculo). O cliente **reduz toda imagem** antes de enviar (o usuário autorizou perder qualidade): `png_base64_from_file` (`app/view/ui/qimages.py`) reduz o maior lado a `MAX_LADO` e salva como **JPEG** (qualidade `QUALIDADE`), achatando alpha sobre branco — fotos/screenshots de vários MB viravam base64 gigante. O nome da função é legado ("png_"); os **decodificadores auto-detectam o formato** (JPEG novo ou PNG já gravado), então nada quebra. O transporte é um **endpoint dedicado** `Entity.load_images`/`save_images` (não viaja no save do mapa, para não inchar o `diagram_relationship_history`); o `save_images` faz um upsert **não-destrutivo** da linha em `entity` antes de gravar (a FK de `entity_image`), então imagens funcionam mesmo numa caixa ainda não salva no mapa. O widget `QImages` (embutido nas abas "Images" dos diálogos de entidade e de vínculo) carrega e grava sozinho, na hora de cada alteração. **As tabelas `entity_image`/`entity_face` precisam da migração no banco live** — ver o bloco de migração comentado (junto de `entity_face`) em `server/data/create.sql`.

Entidades **Other** têm um **subtipo** (`sub_etype`, chave = `md5(nome)`). O **cadastro** dos subtipos válidos e o **rosto default** de cada um são **globais** (nível banco), numa tela própria `DialogSubtypes` (`app/view/dialog_subtypes.py`, aberta pelo item "Sub-tipos" no menu File / toolbar) — não ficam dentro da entidade. Dentro do diálogo da Other, na aba **Actions**, há apenas um combo somente-leitura para **selecionar** um subtipo já existente. Cada subtipo pode ter um **rosto default** (`sub_etype.face_default`, base64) compartilhado por todas as Others dele. No mapa (com `show_face`), o `face_default` do subtipo aparece como **badge** — imagem pequena **antes do nome**, na mesma linha (`MapRelationshipBox.draw_subtype_badge`), somado ao que já é exibido. Mas o **rosto próprio tem preferência**: se a entidade tem `entity_face`, o badge do subtipo **não** aparece. O `load` do servidor (`MapRelationship/001.php`) entrega `face` (próprio) e `subtype_face` (do subtipo) **separados**. Endpoints em `Entity/001.php`: `load_subetypes`, `create_subetype`/`delete_subetype` (gerência global), `set_subetype_face` (rosto default do subtipo), `set_subetype` (atribui um subtipo a uma entidade).

Cada mapa (`MapRelationship`) tem duas configurações no diálogo **Property** (`DialogRelationshipEdit`): **Idioma** (`language`, um de `pt-BR`/`en`/`es` — a lista canônica é `report.IDIOMAS`) e **Exibir PNG de rosto** (`show_face`). O idioma alimenta o prompt do **report** e do **bot de entidades** (via `report.idioma_frase`, único ponto de verdade — o report não é mais fixo em português). Com `show_face` ligado, quando a entidade (pessoa/org/outro) tem rosto, a **imagem substitui a caixinha com o nome** — não desenha retângulo nem texto, só o PNG (`MapRelationshipBox.mostra_rosto`/`draw_face_only`; o `recalc` dimensiona `w`/`h` pela miniatura para a área de clique e as linhas de vínculo baterem na imagem). Sem rosto, a caixa normal com o nome. O servidor só traz os `entity_face` no load do mapa quando `show_face` está ligado, e o efeito de ligar aparece **ao reabrir** o mapa (o load atual não tinha os rostos). Ambos os campos persistem em colunas novas de `diagram_relationship` (mesma migração).

O banco de entidades é **semeado com CTI do MISP Galaxy** (github.com/MISP/misp-galaxy): threat actors, malware, ransomware, RATs — ~7.900 entidades no domain `cyberwar`, com sinônimos (`entity_aka`), referências e relações globais (`entity_simple_association`, entidade↔entidade, ainda sem UI). Convenção: entidade **de origem MISP** tem `id` no formato **UUID** (com hífens); entidade **nativa** tem `id` `hex_hex_hex` (underscores) — isso torna a origem identificável e reversível. Colisões de nome **enriquecem** a entidade existente (não duplicam). Mapeamento, reexecução e rollback em **`docs/MISP-GALAXY.md`**; o importador é `script/misp_import.py`. Panorama de infra e fontes de dados em **`docs/ARQUITETURA.md`**.

### Reports em segundo plano (rolhama)

Um mapa gera um **relatório em PDF** a partir das suas fontes: `app/classlib/report.py` coleta os links das entidades — os da aba References **mais o site oficial (`default_url`) e a Wikipedia (`wikipedia`)** de cada entidade, quando forem URLs http(s), deduplicados —, baixa o texto (até `MAX_REFERENCIAS = 50`, o resto vai listado em "Demais referências"), monta **um único prompt** e manda ao LLM; a saída vira PDF via `QTextDocument`→`QPdfWriter` e é anexada como `Document`.

O **idioma** do mapa (`language`, default `en`; ver *Modelo de domínio*) vai em **toda** chamada ao rolhama e é **reforçado no output**: `report.instrucao_idioma(codigo)` devolve uma instrução forte no próprio idioma-alvo e `Rolhama.gerar(..., idioma_instrucao=...)` a anexa como **última linha** do prompt (recência). Report e bot de entidades passam isso; "linguagem natural" na instrução exclui de propósito as chaves JSON do bot.

- **Um prompt só, não um por referência**, porque o worker do rolhama serializa **globalmente** (uma geração por vez em toda a máquina); cada chamada segura a fila de todos os projetos. O corte de referências existe para caber na **janela de contexto do modelo** — se estourar, o ollama trunca o prompt em silêncio e o modelo responde confiante sobre o pedaço que viu, então `report.py` derruba referências até caber e diz quantas.
- A geração roda no `ReportManager` (`app/view/ui/report_manager.py`), um **singleton de módulo** que vive fora dos diálogos: a `QThread` não pertence ao `DialogDocument`, senão fechar a janela mataria a geração. A GUI só escuta sinais (`progresso`/`concluiu`/`falhou`/`mudou`); a janela principal mostra o estado no botão "Documents".
- A trava entre máquinas é o `ReportJob` (`server/.../ReportJob/001.php`): uma coluna gerada `lock_global` com índice `UNIQUE` garante **um report por vez no domain** sem "verifica e insere" (que teria corrida). Jobs cujo dono sumiu por mais de 45 min são expirados antes de cada aquisição. `ReportManager` também tem uma trava local, que só impede disparar dois no mesmo cliente.

**O cliente do rolhama fala o contrato webapi** (migrado do bddphp antigo, que foi apagado da Hostinger). `app/classlib/rolhama.py` usa `webapi.ClientAPI` (`app/classlib/webapi.py`, cópia literal de `../rolhama/llm/webapi.py`): `enqueue`/`response` por **job UUID**, MAC de autenticação (`K_auth[canal]`), sem 409 nem `remove()`, teto de 64 MiB. A cifra do payload é ChaCha20-Poly1305 por `(part, canal)` via `bdd.seal`/`bdd.open_blob` (o `app/classlib/bdd.py` é **byte a byte idêntico** ao do worker — se divergir, a resposta não decifra). URL vem de `ROLHAMA_WEBAPI_URL` (aceita `ROLHAMA_BDD_URL` por compat), chave de `ROLHAMA_BDD_KEY`, ambas do `~/.env`.

O webapi ainda **não tem rota de alocação** de canal (é pendência do lado rolhama — `../rolhama/llm/CANAIS.md`), então o canal é **fixo por projeto**, semeado no servidor e mapeado em `CANAL_POR_PROJETO`: report (`"cml"`) → **507**, bot de entidades (`"cml/entidades"`) → **508**, sobrescrevíveis por env (`CML_ROLHAMA_CANAL`, `CML_ROLHAMA_CANAL_ENTIDADES`). Projetos diferentes precisam de canais diferentes porque a mesma chave decifraria a resposta um do outro. O `Rolhama.alocar()` sobreviveu só como compat — hoje devolve o canal fixo, sem ir ao servidor. Contrato completo em `../rolhama/llm/INTEGRACAO.md`; para atualizar o transporte, recopie `webapi.py` e `bdd.py` de `../rolhama/llm/`.

**A confirmar do lado do servidor:** que os canais 507/508 estejam semeados e sendo atendidos pelo worker (o `CANAIS.md` os lista na faixa da semente 500–510, mas marcados "livres" — o CML não aparece na tabela de consumidores).

**A "máquina 90" (o host do rolhama/ollama):** GPU **RTX 5060 16 GB**. Modelo default `qwen2.5:14b-instruct-q6_K` (`report.py`, sobrescrevível por `CML_REPORT_MODELO`; usado por report **e** bot de entidades) — q6_K + 16k de contexto ≈ ~15 GB, encaixa justo na 16 GB; se der OOM, baixar `ROLHAMA_OLLAMA_NUM_CTX` (12288/8192) no `~/.env` **da máquina 90** ou voltar ao Q4. O worker **serializa globalmente** (uma geração por vez na máquina), por isso o report manda um prompt só. Panorama de infra e fontes de dados em `docs/ARQUITETURA.md`.

### App web (somente leitura)

`server/webpage/` é um app PHP MVC próprio (não JSON-RPC) para **visualizar** mapas e baixar documentos pelo navegador. Entra por `server/webpage/index.php`, que escolhe o domain (reusa `Mysql::domains()` do `data/config.json`) e redireciona para a lista. É servido no caminho `.../cml/webpage/`. Estrutura clássica `controller/`/`model/`/`view/`/`service/`, com os assets em `public/`.

O canvas JS do mapa (`view/relationship/relationship.php`) **desenha os rostos** quando o mapa está com `show_face`: o rosto próprio (`entity_face`) substitui a caixa e o rosto default do subtipo (`sub_etype.face_default`) vira badge (o próprio tem preferência). O modelo (`model/relationship/`) só carrega os base64 quando `show_face` está ligado. As imagens vão como data URI que auto-detecta JPEG/PNG. As **"Relações"** (lista textual) ficam em **aba própria**, separadas do mapa. Abas: Mapa · Relações · Documentos · Referências.

### Os bots são plug-ins

Os bots ficam em `app/bot/<pais>/<nome>/`, cada um um `config.json` mais um módulo. Hoje existem quatro em `app/bot/brazil/`: `wikipedia` (scrape), `wayback` (gravação no Wayback), `referencias` (busca links candidatos para uma entidade via Wikipedia/DuckDuckGo) e `entidades` (extrai sujeitos e vínculos de uma URL pelo rolhama, com `format=json`, num canal/projeto próprio — `Rolhama(projeto="cml/entidades")` — separado do canal do report). O `config.json`:

```json
{"button": "Load", "path": "bot/brazil/wikipedia/search.py", "class": "DialogBotWikipedia", "module": "dialogbotwikipedia"}
```

O `app/view/ui/qbot.py` renderiza o botão e carrega a classe no momento do clique, via `importlib.util.spec_from_file_location`, instanciando como `cls(parent, obj)`, em que `obj` é a entity ou a reference que está sendo editada. Para adicionar um bot: crie o diretório e depois coloque um widget `QBot(self, <obj>, "bot/.../config.json")` em um diálogo (veja `dialog_entity_generic.py` e `dialogreference.py`).

### Shell da interface

O `application.py` executa o `DialogConnect` **antes** de criar a janela principal e encerra a menos que o `Server.status` esteja setado. A janela principal é um `QMdiArea` cujos filhos são instâncias de `MdiMap`; os menus e toolbars são construídos, mas várias ações estão comentadas. Os diálogos ficam em `app/view/`, como `dialog_*.py`, e os widgets reutilizáveis em `app/view/ui/`.
