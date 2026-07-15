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

### Os bots são plug-ins

Os bots (scrape da Wikipedia, gravação no Wayback) ficam em `app/bot/<pais>/<nome>/`, como um `config.json` mais um módulo:

```json
{"button": "Load", "path": "bot/brazil/wikipedia/search.py", "class": "DialogBotWikipedia", "module": "dialogbotwikipedia"}
```

O `app/view/ui/qbot.py` renderiza o botão e carrega a classe no momento do clique, via `importlib.util.spec_from_file_location`, instanciando como `cls(parent, obj)`, em que `obj` é a entity ou a reference que está sendo editada. Para adicionar um bot: crie o diretório e depois coloque um widget `QBot(self, <obj>, "bot/.../config.json")` em um diálogo (veja `dialog_entity_generic.py` e `dialogreference.py`).

### Shell da interface

O `application.py` executa o `DialogConnect` **antes** de criar a janela principal e encerra a menos que o `Server.status` esteja setado. A janela principal é um `QMdiArea` cujos filhos são instâncias de `MdiMap`; os menus e toolbars são construídos, mas várias ações estão comentadas. Os diálogos ficam em `app/view/`, como `dialog_*.py`, e os widgets reutilizáveis em `app/view/ui/`.
