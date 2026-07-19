# Import do MISP Galaxy → CML

Como o CML é semeado com inteligência de ameaças do [MISP Galaxy](https://github.com/MISP/misp-galaxy):
o que é, o mapeamento, o que já foi importado, e como reexecutar/estender/reverter.

## O que é o MISP Galaxy

**Não é um banco de dados nem uma API** — é um conjunto de **arquivos JSON** num repositório Git,
mantido pela comunidade MISP, com conhecimento estruturado de CTI. Cada arquivo é uma *galaxy*
(categoria) contendo *clusters* → uma lista de *values* (entidades). É aberto (majoritariamente
CC0). Se baixa e se lê; não há conexão em runtime.

```bash
git clone --depth 1 https://github.com/MISP/misp-galaxy.git   # dados em clusters/*.json
```

Estrutura de um *value* (ex.: `APT1` em `clusters/threat-actor.json`):

```json
{
  "value": "APT1",
  "uuid": "1cb7e1cc-d695-42b1-92f4-fd0112a3c9be",
  "description": "PLA Unit 61398 ...",
  "meta": { "synonyms": ["COMMENT PANDA", "Comment Crew", ...],
            "refs": ["https://...", ...], "country": "CN" },
  "related": [ { "dest-uuid": "6a2e...", "type": "similar" } ]
}
```

## Mapeamento MISP → CML

| MISP | CML | Observação |
|---|---|---|
| `value` | `entity.text_label` | — |
| `uuid` | `entity.id` (nas **novas**) | preserva `related` e permite reimportar sem duplicar |
| `description` | `entity.description` | — |
| `meta.synonyms` | `entity_aka` (id = `md5(entity_id|synonym)`) | — |
| `meta.refs` | `diagram_relationship_element_reference` | **capadas a 8/entidade** (`REFS_CAP`) |
| galaxy → etype/sub_etype | `entity.etype` + `sub_etype` | ver tabela abaixo |
| `related.dest-uuid` | `entity_simple_association` (from/to) | só **relações internas** (ambas as pontas importadas) |

**Galaxy → tipo no CML:**

| Galaxy | etype | sub_etype |
|---|---|---|
| `threat-actor` | `organization` | — |
| `malpedia` | `other` | `malware` |
| `mitre-malware` | `other` | `malware` |
| `ransomware` | `other` | `ransomware` |
| `rat` | `other` | `rat` |

## Convenção de id (importante)

- **Entidade nova** → `id` = o **UUID do MISP** (formato `8-4-4-4-12`, com **hífens**).
- **Entidade nativa do CML** → `id` no formato `hex_hex_hex` (com **underscores**).

Isso torna a origem MISP **identificável e reversível**: `id LIKE '%-%-%-%-%'` seleciona só o que
veio do MISP.

## Colisões de nome (enriquecimento, sem duplicar)

Se o nome de um *value* já existe no CML (ex.: **APT29**, **Lazarus** — que você já tinha nos
mapas), o importer **não cria duplicata**: mantém a entidade existente (com o id nativo dela) e só
**anexa os `aka`/`refs` do MISP**. O dedup também vale **entre galaxies** dentro do mesmo import
(o mesmo malware em `malpedia` e `mitre-malware` vira uma só entidade).

## O que já foi importado (jul/2026)

Escopo: **threat-actor + malware** (`malpedia`, `ransomware`, `mitre-malware`, `rat`). Resultado no
domain `cyberwar`:

- entidades: **311 → 7.881** (7.570 novas + 383 enriquecidas por nome)
- `entity_aka`: **4.176** · references: **23.743** · `entity_simple_association`: **1.065**
- sub_etypes criados: `malware`, `ransomware`, `rat`
- 2 `revoked` ignoradas; ~12.758 relações apontando para **fora do escopo** (ex.: técnicas MITRE)
  foram ignoradas.

Ainda **não importados**: tools/botnet/exploit-kit, country, sector, vendors/agencies, e as galaxies
não-CTI (firearms, naics, nice-framework, sigma-rules…). As **técnicas MITRE** (attack-pattern etc.)
são taxonomia — melhores como `classification`/`sub_etype` do que como caixas.

## Países com bandeira (seed à parte)

A galaxy **`country`** do MISP (252 países) dá nome + código **ISO** (`meta.ISO`), mas **todos os
values compartilham o mesmo `uuid`** — então o id de cada país é um **`uuid5(ISO)`** determinístico
(formato UUID, reversível como o resto). A **bandeira** vem do **flagcdn** (`flagcdn.com/w320/<iso>.png`,
PNG) e é gravada como **rosto próprio** (`entity_face`), etype `other`. Colisões de nome enriquecem a
entidade existente (ex.: `Israel`, `United States of America` já nos mapas ganharam a bandeira, sem
duplicar). Com `show_face`, o país vira a bandeira no mapa (cliente e web).

Feito (jul/2026): 236 países novos + 14 enriquecidos, 250 bandeiras (2 territórios sem bandeira no
flagcdn). Reexecutar:

```bash
python3 script/country_seed.py --country /caminho/misp-galaxy/clusters/country.json --write
```

## Reexecutar / estender

O importer é **idempotente** (`ON DUPLICATE KEY`) — rodar de novo não duplica. Para incluir mais
galaxies, edite a lista `GALAXIES` em `script/misp_import.py` (`(arquivo, etype, sub_etype)`) e rode.

```bash
# 1) ter o clone do misp-galaxy (git clone --depth 1 ...)
# 2) credenciais de banco no ~/.env (CYBERWARFARE_DB_*), como no DEPLOY.md
python3 script/misp_import.py --galaxies /caminho/misp-galaxy/clusters --dry-run   # só mostra
python3 script/misp_import.py --galaxies /caminho/misp-galaxy/clusters --write     # grava
```

O `--dry-run` (padrão) lê o banco só para comparar e reporta o que entraria, **sem gravar**. O
`--write` grava em **uma transação** (multi-row INSERT; conexão remota exige isso para não fazer
milhares de round-trips). Usa `utf8mb4` (nomes/descrições em CJK).

## Reverter

As entidades MISP têm `id` no formato UUID. Para desfazer o import (cuidado — apaga também o que foi
enriquecido? **não**: as enriquecidas têm id nativo e sobrevivem; some só o que era puramente MISP):

```sql
-- ordem respeita as FKs (filhas primeiro)
DELETE FROM entity_aka                          WHERE entity_id LIKE '%-%-%-%-%';
DELETE FROM diagram_relationship_element_reference WHERE entity_id LIKE '%-%-%-%-%';
DELETE FROM entity_simple_association WHERE entity_from_id LIKE '%-%-%-%-%' OR entity_to_id LIKE '%-%-%-%-%';
DELETE FROM entity WHERE id LIKE '%-%-%-%-%' AND etype <> 'link';
```

Os `aka`/`refs` anexados às entidades **enriquecidas** (id nativo) não são removidos por isso — se
precisar, filtre pelos ids dos `aka`/`refs` (o importer gera id `md5(entity_id|conteudo)`).
