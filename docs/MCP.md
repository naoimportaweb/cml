# Servidor MCP `cml-transforms`

Expõe os **transforms** do CML (SPEC.md §2) ao Claude Code: listar quais servem a um tipo de
entidade e executar um deles. Arquivo: `mcp/cml_transforms.py`, registrado no `.mcp.json`
(sem segredo — chaves e URLs vêm do `~/.env` da estação). Stdio, JSON-RPC 2.0, só stdlib.

O outro servidor MCP do projeto, `cml-remoto`, opera a hospedagem (deploy, SQL, logs); este
opera a **descoberta de dados**. Não se misturam.

## Princípios

- **Só propõe.** `executar_transform` devolve entidades e vínculos candidatos; nunca grava em
  mapa, banco ou servidor. Entrar no mapa é decisão do analista, no painel de Proposta.
- **Mesmo núcleo da GUI** (`app/transform/nucleo.py` e `contexto.py`, sem Qt): cache por
  `(transform, versão, entrada)`, log em `~/.cml_cache/transform.log`, rota `direta`/`tor`,
  backend de LLM `rolhama` (padrão, canal 510) ou `ollama` (opt-in).
- **Isolamento.** Cada execução roda em subprocesso, com timeout (padrão 300 s, máx. 900 s);
  ao estourar, o grupo de processos inteiro é morto. O `print()` de um transform não corrompe
  o protocolo (o stdout do worker é reservado ao resultado).
- **Segredo.** Nenhuma ferramenta mostra valor do `~/.env`; só `SIM`/`NÃO` para "existe".

## Ferramentas

| Ferramenta | O que faz |
|---|---|
| `listar_transforms(etype?, sub_etype?, fonte?)` | id, nome, fonte, entrada/saída, rota, rede, `chave_env_presente` (SIM/NÃO) e motivo de indisponibilidade |
| `executar_transform(id, text_label, etype, …)` | roda e devolve `entidades`, `vinculos`, `avisos`, `do_cache`, `proposta_somente`. Opcionais: `sub_etype`, `small_label`, `description`, `wikipedia`, `default_url`, `urls` (máx. 10), `idioma` (`pt-BR`/`en`/`es`), `entity_id`, `timeout` |
| `ver_log(n=20)` | últimas execuções (quando, transform, situação, tempo, rota, LLM) |
| `limpar_cache(transform_id?)` | apaga só os `.json` dentro de `~/.cml_cache`; o log fica; recusa link simbólico e caminho fora do cache |
| `backend_status()` | backend de LLM ativo, rota padrão, se `CML_OLLAMA_URL`/`ROLHAMA_BDD_KEY`/`CML_CRAUDIO_PORTA` estão definidos |

Erros de argumento (tipo errado, `etype` que o transform não aceita, URL sem `http(s)`, etc.)
voltam como `isError` com mensagem curta, antes de gastar rede ou fila de LLM. A saída é
limitada a ~60 KB: passando disso, as últimas entidades são cortadas (e os vínculos que
ficariam com ponta solta), com aviso — o JSON continua válido.

## Limites conhecidos

- Transforms que dependem de **sessão no servidor do CML** (`Base`: busca de entidades,
  `Entity.associations`) falham com erro claro quando não há login: o worker não faz o
  handshake RSA/sessão da GUI.
- Transform de **IA** pode esperar na fila do `rolhama` (e a Máquina 90 pode estar desligada);
  use `timeout` maior ou espere o erro de tempo esgotado.
- Transform de **scraping** exige o `craudiowebot` rodando com `--servir`.

## Teste

```bash
python3 mcp/teste_cml_transforms.py
```

Fala o protocolo MCP por stdin/stdout contra transforms de teste criados num diretório
temporário. Usa dois ganchos que existem **só para o teste** (não defina em uso normal):
`CML_TX_RAIZ` (outro diretório de transforms) e `CML_TX_CACHE` (outro diretório de cache).
Não usa rede nem LLM.
