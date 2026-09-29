# EDITORIAL.md — como preencher um mapa de vínculos

Regras editoriais para quem alimenta o CML (pessoa, script ou bot), extraídas da revisão dos
sete primeiros mapas do domain `corrupcao` (2026-09-22). O princípio que resume todas: **o mapa
é lido de relance; o detalhe mora nos diálogos** (aba References, campo Descrição). Quem vai
escrever código que grava mapa deve ler também o `CLAUDE.md` (modelo de domínio) — este
arquivo é sobre *conteúdo*, não sobre transporte.

## 1. Entidade = só o nome

- A **caixinha** mostra o nome e mais nada: "José Dirceu", "Banco Master", "Mensalão". Nada de
  "José Dirceu · ex-ministro · condenado · R$ 1,1 mi".
- **Nickname / Acronym** vai no campo próprio (`small_label`): "Lula", "PT", "STF", "Dino".
  Atenção ao desenho: para pessoa e "outro" o apelido **substitui** o nome na caixa; para
  organização aparece como "Nome (SIGLA)". Por isso apelido é apelido — não é lugar de cargo.
- **Nome completo no `text_label`**: "Luiz Inácio Lula da Silva" (apelido "Lula"), "Partido dos
  Trabalhadores" (sigla "PT"). O apelido é o que se lê no mapa; o nome é o que identifica.
- **Descrição da entidade descreve a entidade** — quem ela é, em qualquer contexto: "Político
  brasileiro, ex-metalúrgico e sindicalista do ABC paulista, fundador do PT; presidente da
  República 2003–2010 e desde 2023". Nunca o que *esta* matéria diz sobre ela: a entidade é
  **global** (compartilhada por todos os mapas do domain) e um texto preso a uma notícia fica
  errado no mapa seguinte.
- **O que a entidade era naquele momento** ("ex-presidente da Câmara", "procurador-geral da
  República", "candidato a deputado federal por SP") vira uma **referência datada** dentro da
  entidade: título = o cargo/condição, data = a da fonte, descrição = o trecho que sustenta,
  link = a fonte. Uma entidade que aparece em cinco matérias tem cinco dessas referências — é o
  histórico dela.

## 2. Vínculo = um verbo, curto

- O rótulo do vínculo é **um verbo numa frase curtíssima**: "Financiou", "Condenados",
  "Pediu vista", "Convidou p/ comitê", "Cabo eleitoral", "Titular da pasta", "Casada com".
  Sem parênteses, sem valores, sem lista de nomes, sem ano no texto.
- **Data e período vão na relação**, não no rótulo: cada ponta do vínculo tem
  `start_date`/`end_date`/`format_date`. Use `yyyy` quando só o ano importa (o convite de
  2022), `MM/yyyy` para mês (a nota de março/2026), `yyyy-MM-dd` quando há o dia.
- **Vínculos do mesmo tipo se juntam** num só com várias pontas: quatro "Financiou R$ …"
  viram um "Financiou" `PT → Dirceu, Vargas, Cunha, Delúbio`; quatro "Condenado …" viram um
  "Condenados" `→ Mensalão, Petrolão`. O que se perde na ponta individual (quem foi condenado em
  qual escândalo) vai para a descrição do vínculo.
- **A descrição do vínculo é o próprio fato** — ali, sim, o texto pode vir da matéria, com
  valores, datas e citações: "Dirceu recebeu R$ 1,1 milhão do PT; Cunha R$ 1,1 milhão; Vargas
  R$ 841 mil; Delúbio R$ 780 mil".
- Direção importa: `from` é quem age, `to` é quem recebe ("PT → Financiou → candidatos";
  "Ciro Soares → Intermediou → Vorcaro, Gonet").

## 3. Descrição e fonte

- **Descrição é o campo do texto longo** — caprichar, em todas as entidades e vínculos. É
  "um campo enorme para descrever".
- **Sem linha "Fonte: …" na descrição.** A fonte é a referência: título da matéria/vídeo,
  `link1` = URL, data de publicação, descrição = o trecho relevante. Todo elemento do mapa
  (entidade *e* vínculo) recebe uma referência da fonte que o justificou.
- **Vídeo** é fonte como qualquer outra: a referência leva a URL do vídeo; o texto é a
  transcrição (guardada fora do mapa). Título = o título do vídeo.
- **Duas fontes sobre o mesmo fato** = duas referências no mesmo elemento (a matéria da Veja
  *e* a da Gazeta em "Cabo eleitoral"), não dois mapas. Uma segunda matéria sobre o **mesmo
  caso** enriquece o mapa existente (referências novas, datas nas pontas, uma ou outra
  entidade que faltava) em vez de gerar um mapa quase igual.
- O `default_reference` do mapa é a URL da fonte principal; o `keyword` lista nomes e temas
  para a busca da lista de mapas.

## 4. Antes de criar, procurar

- **Toda entidade (pessoa, grupo, "outro") é buscada antes de ser criada** — pela função de
  busca do cliente (`Entity.search`, a mesma do diálogo *Load*), que casa nome e apelido.
  Existe? Reaproveita pelo `id` (`addEntity(..., entity_id_=id)`). Não existe? Cria.
- Entidade reaproveitada **carrega o que já tem**: descrição, apelido e **todas as
  referências** acumuladas nos outros mapas — e só então recebe a referência nova. O save do
  mapa poda referências que não forem reenviadas; reaproveitar sem carregar apaga o histórico.
  (Hoje a busca devolve só a linha da entidade, sem referências; script precisa reuni-las dos
  mapas em que ela aparece — ver "Armadilhas".)
- Nome canônico e estável: "Alexandre de Moraes", não "Moraes"; "Supremo Tribunal Federal",
  não "STF". Apelidos e siglas entram no `small_label`, e é por eles que a busca também acha.
- Em dúvida entre dois candidatos parecidos (mesma pessoa? mesma empresa?), perguntar — e
  registrar a decisão na descrição ("Prime Aviation, referida também como Prime You").

## 5. Fluxo de uma matéria nova

1. Baixar o texto (`curl` com **User-Agent de Firefox atualizado**; portais bloqueiam UA de
   robô) ou usar a transcrição, se for vídeo. Guardar título, autor, data e URL.
2. Listar atores (pessoas, organizações, "outros" — eventos, escândalos, contratos, voos) e
   fatos (verbo + quem + quem + quando).
3. Para cada ator: buscar; reaproveitar ou criar; bio na descrição; cargo daquele momento como
   referência datada.
4. Para cada fato: um vínculo com verbo curto, datas nas pontas, descrição com o detalhe,
   referência da fonte. Fatos iguais com atores diferentes → um vínculo só, várias pontas.
5. Salvar, **reabrir e conferir**: contagem de elementos, nenhuma descrição vazia, nenhuma
   entidade duplicada, nenhuma órfã.
6. Olhar o desenho (a página web `webpage/view/relationship/relationship.php?id=…&domain=…`
   serve para isso) e arrastar o que ficou sobreposto.

## 6. Armadilhas conhecidas

- **`small_label` substitui o nome** no desenho de pessoa/outro — um "cargo" ali esconde quem é
  a pessoa. Corrigido nos sete mapas; regra em §1.
- **Descrição do vínculo não era carregada** pelo `load_data` (só a das entidades); qualquer
  save gravava vazio por cima. Corrigido em `app/classlib/relationship/maprelationship.py`
  (2026-09-22). Cliente aberto com o código antigo ainda apaga — reinicie.
- **Inserir entidade existente pela GUI (*Load*) e salvar apaga as referências antigas
  dela**: o `Entity.search` não traz referências e o save poda o que não veio. Furo aberto do
  lado do app; até o conserto, carregar os mapas em que a entidade aparece e reenviar as
  referências (é o que `cml_mapa.py` faz).
- **Um vínculo não some com um save só**: o servidor só poda as pontas
  (`diagram_relationship_link`) dos elementos ainda presentes. Para remover um vínculo:
  esvaziar `to`/`from` e salvar; depois tirar o elemento e salvar de novo. A entidade global do
  vínculo removido fica órfã em `entity` — limpar por SQL (`etype='link'` sem elemento).
- **Entidade "outro" que é evento** (um voo, um julgamento, um contrato) recebe a data no
  título quando isso a identifica ("Voo São Paulo–Rio de 20/08/2025") — é o que a diferencia de
  outro voo. Já pessoa e organização nunca levam data no nome.
