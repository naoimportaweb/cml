
create table entity_aka(
    id VARCHAR(128) PRIMARY KEY,
    entity_id VARCHAR(128) NOT NULL,
    name varchar(255) NOT NULL
);


create table entity_simple_association (
    id VARCHAR(128) PRIMARY KEY,
    entity_from_id VARCHAR(128) NOT NULL,
    entity_to_id VARCHAR(128) NOT NULL
);

create table sub_etype (
    id VARCHAR(128) PRIMARY KEY,
    icon varchar(255),
    name varchar(255) NOT NULL,
    face_default LONGTEXT
);

create table entity_image (
    id VARCHAR(128) PRIMARY KEY,
    entity_id VARCHAR(128) NOT NULL,
    png_base64 LONGTEXT NOT NULL,
    creation_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE entity ADD COLUMN sub_etype_id varchar(128);
ALTER TABLE entity ADD COLUMN icon varchar(255);
ALTER TABLE diagram_relationship ADD COLUMN default_reference VARCHAR(255);

ALTER TABLE entity_aka ADD FOREIGN KEY (entity_id) REFERENCES entity(id);
ALTER TABLE entity_image ADD FOREIGN KEY (entity_id) REFERENCES entity(id);
ALTER TABLE entity_simple_association ADD FOREIGN KEY (entity_from_id) REFERENCES entity(id);
ALTER TABLE entity_simple_association ADD FOREIGN KEY (entity_to_id)   REFERENCES entity(id);
ALTER TABLE entity ADD FOREIGN KEY (sub_etype_id)   REFERENCES sub_etype(id);

# --------------- INSTALAÇAO -------------------------------------

create table person(
    id VARCHAR(128) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    usertype INT NOT NULL DEFAULT 0,
    status INT NOT NULL DEFAULT 0,
    salt VARCHAR(255) NOT NULL
);

create table person_sesion(
    id VARCHAR(128) PRIMARY KEY,
    person_id VARCHAR(128) NOT NULL,
    simetric_key VARCHAR(255) NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table person_enter(
    id VARCHAR(128) PRIMARY KEY,
    person_id VARCHAR(128),
    key_enter TEXT,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table diagram_relationship (
    id VARCHAR(128) PRIMARY KEY,
    person_id VARCHAR(128) NOT NULL,
    keyword VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    visibility INT NOT NULL DEFAULT 0,
    language VARCHAR(16) NOT NULL DEFAULT 'en',
    show_face INT NOT NULL DEFAULT 0,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table diagram_relationship_history (
    id VARCHAR(128) PRIMARY KEY,
    person_id VARCHAR(128) NOT NULL,
    diagram_relationship_id VARCHAR(128) NOT NULL,
    json LONGTEXT NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table diagram_relationship_lock(
    id VARCHAR(128) PRIMARY KEY,
    diagram_relationship_id VARCHAR(128) NOT NULL,
    person_id VARCHAR(128) NOT NULL,
    lock_time DATETIME NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table entity (
    id VARCHAR(128) PRIMARY KEY,
    text_label VARCHAR(255) NOT NULL,
    small_label VARCHAR(255) DEFAULT NULL,
    description LONGTEXT,
    data_extra LONGTEXT,
    wikipedia VARCHAR(255),
    default_url VARCHAR(255),
    start_date         DATE DEFAULT NULL,
    end_date           DATE DEFAULT NULL,
    format_date         VARCHAR(255) DEFAULT 'yyyy-MM-dd',
    etype VARCHAR(255) NOT NULL,
    sub_etype_id VARCHAR(255) NOT NULL,
    icon varchar(255),
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table entity_aka(
    id VARCHAR(128) PRIMARY KEY,
    entity_id VARCHAR(128) NOT NULL,
    name varchar(255) NOT NULL
);


create table entity_simple_association (
    id VARCHAR(128) PRIMARY KEY,
    entity_from_id VARCHAR(128) NOT NULL,
    entity_to_id VARCHAR(128) NOT NULL
);

create table sub_etype (
    id VARCHAR(128) PRIMARY KEY,
    icon varchar(255),
    name varchar(255) NOT NULL,
    face_default LONGTEXT
);

create table entity_image (
    id VARCHAR(128) PRIMARY KEY,
    entity_id VARCHAR(128) NOT NULL,
    png_base64 LONGTEXT NOT NULL,
    creation_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

# ==========================================================================================
# MIGRACAO para bancos ja em producao (ex.: cyberwar). O deploy NAO altera bancos existentes
# (ver DEPLOY.md), entao rodar isto a mao uma vez. Instalacoes novas ja saem corretas.
#
#   -- Imagens da entidade (lista base64) — reaproveita a tabela entity_image (troca path):
#   ALTER TABLE entity_image DROP COLUMN path,
#       ADD COLUMN png_base64 LONGTEXT NOT NULL,
#       ADD COLUMN creation_time DATETIME DEFAULT CURRENT_TIMESTAMP;
#   -- Rosto (1 por entidade) — tabela nova (entity_face, logo abaixo).
#   -- Idioma e "exibir rosto" por mapa:
#   ALTER TABLE diagram_relationship
#       ADD COLUMN language VARCHAR(16) NOT NULL DEFAULT 'en',
#       ADD COLUMN show_face INT NOT NULL DEFAULT 0;
#   -- Rosto default por subtipo (entidades Other):
#   ALTER TABLE sub_etype ADD COLUMN face_default LONGTEXT DEFAULT NULL;
# ==========================================================================================

# Rosto (imagem principal, 1 por entidade). Tabela propria em vez de coluna em entity:
# o save_images roda independente do save do mapa, entao precisa gravar sem depender de
# a linha em entity ja existir. Sem FK de proposito.
create table entity_face (
    entity_id VARCHAR(128) PRIMARY KEY,
    png_base64 LONGTEXT NOT NULL,
    creation_time DATETIME DEFAULT CURRENT_TIMESTAMP
);




create table classification(
    id VARCHAR(128) PRIMARY KEY,
    text_label VARCHAR(255) NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table classification_item(
    id VARCHAR(128) PRIMARY KEY,
    classification_id VARCHAR(128) NOT NULL,
    text_label VARCHAR(255) NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table entity_classification_item (
    id VARCHAR(128) PRIMARY KEY,
    classification_item_id VARCHAR(128) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    start_date         DATE DEFAULT NULL,
    end_date           DATE DEFAULT NULL,
    format_date         VARCHAR(255) DEFAULT 'yyyy-MM-dd',
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table diagram_relationship_element(
    id VARCHAR(128) PRIMARY KEY,
    diagram_relationship_id VARCHAR(128) NOT NULL,
    entity_id  VARCHAR(128) NOT NULL,
    start_date         DATE DEFAULT NULL,
    end_date           DATE DEFAULT NULL,
    format_date         VARCHAR(255) DEFAULT 'yyyy-MM-dd',
    x INT NOT NULL, y INT NOT NULL, w INT NOT NULL, h INT NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table diagram_relationship_element_reference( 
    id VARCHAR(128) PRIMARY KEY,
    entity_id VARCHAR(128) NOT NULL,
    description TEXT DEFAULT NULL,
    title VARCHAR(255), link1 TEXT, link2 TEXT, link3 TEXT,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table diagram_relationship_link(
    id VARCHAR(128) PRIMARY KEY,
    diagram_relationship_element_id VARCHAR(128) NOT NULL,
    diagram_relationship_element_id_reference VARCHAR(128) NOT NULL,
    ltype int NOT NULL,
    start_date         DATE DEFAULT NULL,
    end_date           DATE DEFAULT NULL,
    format_date         VARCHAR(255) DEFAULT 'yyyy-MM-dd',
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table document_type( 
    id VARCHAR(128) PRIMARY KEY,
    name VARCHAR(255),
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table diagram_relationship_document( 
    id VARCHAR(128) PRIMARY KEY,
    diagram_relationship_id VARCHAR(128) NOT NULL,
    document_type_id VARCHAR(128) NOT NULL,
    description TEXT default NULL,
    title VARCHAR(255), link1 TEXT, link2 TEXT, link3 TEXT,
    default_reference VARCHAR(255),
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table organization_chart( 
    id VARCHAR(128) PRIMARY KEY,
    text_label VARCHAR(255) NOT NULL,
    organization_id VARCHAR(128) NOT NULL,
    person_id VARCHAR(128) NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table organization_chart_item( 
    id VARCHAR(128) PRIMARY KEY,
    text_label VARCHAR(255) NOT NULL,
    etype VARCHAR(255) NOT NULL,
    x int DEFAULT 0,
    organization_chart_id VARCHAR(128) NOT NULL,
    organization_chart_item_parent_id VARCHAR(128) DEFAULT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table organization_chart_item_entity( 
    id VARCHAR(128) PRIMARY KEY,
    organization_chart_item_id VARCHAR(128) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    start_date         DATE DEFAULT NULL,
    end_date           DATE DEFAULT NULL,
    format_date         VARCHAR(255) DEFAULT 'yyyy-MM-dd',
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table organization_chart_history (
    id VARCHAR(128) PRIMARY KEY,
    person_id VARCHAR(128) NOT NULL,
    organization_chart_id VARCHAR(128) NOT NULL,
    json LONGTEXT NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);


ALTER TABLE entity_aka ADD FOREIGN KEY (entity_id) REFERENCES entity(id);
ALTER TABLE entity_image ADD FOREIGN KEY (entity_id) REFERENCES entity(id);
ALTER TABLE entity_simple_association ADD FOREIGN KEY (entity_from_id) REFERENCES entity(id);
ALTER TABLE entity_simple_association ADD FOREIGN KEY (entity_to_id)   REFERENCES entity(id);
ALTER TABLE entity ADD FOREIGN KEY (sub_etype_id)   REFERENCES sub_etype(id);

ALTER TABLE diagram_relationship_document ADD FOREIGN KEY (document_type_id) REFERENCES document_type(id);
ALTER TABLE diagram_relationship_document ADD FOREIGN KEY (diagram_relationship_id) REFERENCES diagram_relationship(id);
ALTER TABLE diagram_relationship_history ADD FOREIGN KEY (diagram_relationship_id) REFERENCES diagram_relationship(id);
ALTER TABLE diagram_relationship_history ADD FOREIGN KEY (person_id) REFERENCES person(id);
ALTER TABLE person_enter ADD FOREIGN KEY (person_id) REFERENCES person(id);
ALTER TABLE person_sesion ADD FOREIGN KEY (person_id) REFERENCES person(id);
ALTER TABLE diagram_relationship ADD FOREIGN KEY (person_id) REFERENCES person(id);
ALTER TABLE diagram_relationship_lock ADD FOREIGN KEY (person_id) REFERENCES person(id);
ALTER TABLE diagram_relationship_lock ADD FOREIGN KEY (diagram_relationship_id) REFERENCES diagram_relationship(id);
ALTER TABLE diagram_relationship_element ADD FOREIGN KEY (entity_id) REFERENCES entity(id);
ALTER TABLE diagram_relationship_element ADD FOREIGN KEY (diagram_relationship_id) REFERENCES diagram_relationship(id);
ALTER TABLE diagram_relationship_element_reference ADD FOREIGN KEY (entity_id) REFERENCES entity(id);
ALTER TABLE diagram_relationship_link ADD FOREIGN KEY (diagram_relationship_element_id) REFERENCES diagram_relationship_element(id);
ALTER TABLE diagram_relationship_link ADD FOREIGN KEY (diagram_relationship_element_id_reference) REFERENCES diagram_relationship_element(id);
ALTER TABLE person ADD CONSTRAINT UniqueUsername UNIQUE (username); 
ALTER TABLE person ADD CONSTRAINT UniqueEmail UNIQUE (email); 
ALTER TABLE organization_chart ADD FOREIGN KEY (organization_id) REFERENCES entity(id);
ALTER TABLE organization_chart ADD FOREIGN KEY (person_id) REFERENCES person(id);
ALTER TABLE organization_chart_item ADD FOREIGN KEY (organization_chart_id) REFERENCES organization_chart(id);
ALTER TABLE organization_chart_item ADD FOREIGN KEY (organization_chart_item_parent_id) REFERENCES organization_chart_item(id);
ALTER TABLE organization_chart_item_entity ADD FOREIGN KEY (organization_chart_item_id) REFERENCES organization_chart_item(id);
ALTER TABLE organization_chart_item_entity ADD FOREIGN KEY (entity_id) REFERENCES entity(id);
ALTER TABLE organization_chart_history ADD FOREIGN KEY (organization_chart_id) REFERENCES organization_chart(id);
ALTER TABLE organization_chart_history ADD FOREIGN KEY (person_id) REFERENCES person(id);



# --------------------------- LIMPANDO -------------------------

-- USUARIO SEMEADO SEM SENHA UTILIZAVEL.
--
-- Antes esta linha trazia o valor da coluna `password` preenchido. Isso era uma credencial
-- publicada: o login comparava o valor recebido DIRETO com a coluna, entao quem lesse este
-- arquivo entrava, sem precisar quebrar nada. O arquivo esta em repositorio.
--
-- Agora a coluna nasce vazia, e o `__confere_senha__` do session.php recusa senha vazia: a
-- conta existe, mas NAO entra ate alguem definir a senha (pelo Register, ou por um UPDATE com
-- password_hash feito por quem administra). Conta que nao entra e melhor que conta com a
-- chave publicada.
insert into person (id, username, name, password, salt, email) values ('1', 'nao.importa.web', 'nao.importa.web', '', '1111', '');

INSERT INTO classification(id, text_label) values('1', "Posicionamento Político");
INSERT INTO classification_item(id, classification_id, text_label) values('1', '1', 'Extrema esquerda');
INSERT INTO classification_item(id, classification_id, text_label) values('2', '1', 'Esquerda moderada');
INSERT INTO classification_item(id, classification_id, text_label) values('3', '1', 'Neutro');
INSERT INTO classification_item(id, classification_id, text_label) values('4', '1', 'Direita moderada');
INSERT INTO classification_item(id, classification_id, text_label) values('5', '1', 'Extrema direita');
INSERT INTO classification_item(id, classification_id, text_label) values('14', '1', 'Centro');

INSERT INTO classification(id, text_label) values('2', "Profissão");
INSERT INTO classification_item(id, classification_id, text_label) values('6', '2', 'Jornalista');
INSERT INTO classification_item(id, classification_id, text_label) values('7', '2', 'Político');
INSERT INTO classification_item(id, classification_id, text_label) values('8', '2', 'Empresário');
INSERT INTO classification_item(id, classification_id, text_label) values('9', '2', 'Funcionário público de baixo status');
INSERT INTO classification_item(id, classification_id, text_label) values('10', '2', 'Ministro');
INSERT INTO classification_item(id, classification_id, text_label) values('11', '2', 'Cargo de Indicação Política');


delete from diagram_relationship_link;
delete from diagram_relationship_element_reference;
delete from diagram_relationship_element;
delete from entity;
delete from diagram_relationship;


drop table diagram_relationship_document;
drop table diagram_relationship_link;
drop table diagram_relationship_history;
drop table diagram_relationship_lock;
drop table diagram_relationship_element_reference;
drop table diagram_relationship_element;
drop table entity_classification_item;
drop table entity;
drop table diagram_relationship;
drop table person_sesion;
drop table person_enter;
drop table classification_item;
drop table classification;
drop table document_type;
drop table person;





# ------------- HOMOLOGAÇAO -------------------------------

ALTER TABLE entity ADD COLUMN default_url  VARCHAR(255);
ALTER TABLE entity ADD COLUMN start_date   DATE DEFAULT NULL;
ALTER TABLE entity ADD COLUMN end_date     DATE DEFAULT NULL;
ALTER TABLE entity ADD COLUMN format_date  VARCHAR(255) DEFAULT 'yyyy-MM-dd';
ALTER TABLE diagram_relationship_element ADD COLUMN start_date   DATE DEFAULT NULL;
ALTER TABLE diagram_relationship_element ADD COLUMN end_date     DATE DEFAULT NULL;
ALTER TABLE diagram_relationship_element ADD COLUMN format_date  VARCHAR(255) DEFAULT 'yyyy-MM-dd';
ALTER TABLE diagram_relationship_document ADD COLUMN description TEXT DEFAULT NULL;
ALTER TABLE diagram_relationship_element_reference ADD COLUMN description TEXT DEFAULT NULL;


ALTER TABLE organization_chart_item MODIFY COLUMN organization_chart_item_parent_id VARCHAR(128) DEFAULT NULL;
ALTER TABLE organization_chart_item_entity MODIFY COLUMN id VARCHAR(256) NOT NULL;
ALTER TABLE organization_chart_item ADD COLUMN sequencia int not NULL;
ALTER TABLE organization_chart_item ADD COLUMN x int DEFAULT 0;

ALTER TABLE organization_chart_item_entity ADD COLUMN  start_date         DATE DEFAULT NULL;
ALTER TABLE organization_chart_item_entity ADD COLUMN  end_date           DATE DEFAULT NULL;
ALTER TABLE organization_chart_item_entity ADD COLUMN  format_date         VARCHAR(255) DEFAULT 'yyyy-MM-dd';

-- ============================================================================
-- Documentos (PDF de report) anexados a mapas.
--
-- A diagram_relationship_document que existe acima nao serve: ela tem
-- diagram_relationship_id NOT NULL, ou seja, amarra cada documento a UM mapa. O
-- requisito e o oposto — o mesmo report pode estar em varios mapas. Dai as duas
-- tabelas abaixo. A antiga fica onde esta (nenhum codigo a le) para nao quebrar
-- bases existentes.
--
-- O sha256 e UNIQUE: o mesmo PDF entra uma vez so, e cada mapa que o usa vira uma
-- linha em document_map. E o que faz "o mesmo report em N mapas" nao duplicar bytes.
-- ============================================================================
create table document (
    id VARCHAR(128) PRIMARY KEY,
    sha256 CHAR(64) NOT NULL,
    document_type_id VARCHAR(128) DEFAULT NULL,
    person_id VARCHAR(128) DEFAULT NULL,
    title VARCHAR(255),
    description TEXT DEFAULT NULL,
    bytes BIGINT DEFAULT 0,
    origem VARCHAR(32) DEFAULT 'upload',
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);
ALTER TABLE document ADD CONSTRAINT UQ_document_sha256 UNIQUE (sha256);
ALTER TABLE document ADD FOREIGN KEY (document_type_id) REFERENCES document_type(id);
ALTER TABLE document ADD FOREIGN KEY (person_id) REFERENCES person(id);

create table document_map (
    id VARCHAR(128) PRIMARY KEY,
    document_id VARCHAR(128) NOT NULL,
    diagram_relationship_id VARCHAR(128) NOT NULL,
    person_id VARCHAR(128) DEFAULT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP
);
-- Impede o mesmo documento ser anexado duas vezes ao mesmo mapa.
ALTER TABLE document_map ADD CONSTRAINT UQ_document_map UNIQUE (document_id, diagram_relationship_id);
ALTER TABLE document_map ADD FOREIGN KEY (document_id) REFERENCES document(id);
ALTER TABLE document_map ADD FOREIGN KEY (diagram_relationship_id) REFERENCES diagram_relationship(id);
ALTER TABLE document_map ADD FOREIGN KEY (person_id) REFERENCES person(id);


-- ============================================================================
-- Fila de geracao de report pelo rolhama.
--
-- Por que a tabela existe: o CML tem UM canal no rolhama (507). O CANAIS.md e
-- explicito — "dois projetos nunca compartilham canal: a response de um seria lida
-- pelo outro (mesma chave => mesmo endereco)". Dois reports simultaneos, ainda que
-- de mapas diferentes ou de analistas em maquinas diferentes, colidiriam no 507:
-- um levaria 409 no PUT, ou pior, leria a resposta do outro e anexaria o relatorio
-- errado ao mapa errado. Logo a trava e GLOBAL (um report por vez), nao por mapa.
--
-- lock_global e o mutex, garantido pelo banco: vale 'LOCK' so quando status =
-- 'executando' e NULL nos demais. Como NULL nao colide em UNIQUE, existem quantas
-- linhas concluidas/falhas se queira, mas no maximo UMA executando. Dois clientes
-- disputando: um insere, o outro leva 1062 (Duplicate entry) — sem janela de corrida,
-- diferente de um "SELECT ... e se nao houver, INSERT" feito na aplicacao.
-- ============================================================================
create table report_job (
    id VARCHAR(128) PRIMARY KEY,
    diagram_relationship_id VARCHAR(128) NOT NULL,
    person_id VARCHAR(128) DEFAULT NULL,
    canal INT DEFAULT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'executando',   -- executando|concluido|falhou|cancelado
    progresso VARCHAR(255) DEFAULT NULL,
    document_id VARCHAR(128) DEFAULT NULL,
    referencias_lidas INT DEFAULT 0,
    referencias_total INT DEFAULT 0,
    erro TEXT DEFAULT NULL,
    visto TINYINT NOT NULL DEFAULT 0,                   -- o dono ja viu o aviso de termino?
    creation_time     DATETIME DEFAULT CURRENT_TIMESTAMP,
    modification_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    lock_global CHAR(4) GENERATED ALWAYS AS (IF(status='executando','LOCK',NULL)) STORED
);
ALTER TABLE report_job ADD CONSTRAINT UQ_report_job_lock UNIQUE (lock_global);
ALTER TABLE report_job ADD FOREIGN KEY (diagram_relationship_id) REFERENCES diagram_relationship(id);
ALTER TABLE report_job ADD FOREIGN KEY (person_id) REFERENCES person(id);
ALTER TABLE report_job ADD FOREIGN KEY (document_id) REFERENCES document(id);


-- ============================================================================
-- TIMELINE (terceiro tipo de diagrama).
--
-- A timeline E um documento, como o mapa e o organograma: tem nome, e criada, salva,
-- aparece na lista de abrir e pertence a um usuario. O que ela NAO guarda e posicao de
-- caixa — a posicao de um evento e a data dele.
--
-- diagram_relationship_id e OPCIONAL e define os dois modos de uso:
--   preenchido -> a timeline PROJETA o mapa (vinculo, classificacao, entidade, caixa e
--                 referencia com data) e soma os eventos proprios;
--   NULL       -> timeline solta, so com os eventos que o analista marcar.
-- ============================================================================
create table diagram_timeline (
    id VARCHAR(128) PRIMARY KEY,
    text_label VARCHAR(255) NOT NULL,
    keyword VARCHAR(255) DEFAULT NULL,
    diagram_relationship_id VARCHAR(128) DEFAULT NULL,
    person_id VARCHAR(128) NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);
ALTER TABLE diagram_timeline ADD FOREIGN KEY (diagram_relationship_id) REFERENCES diagram_relationship(id);
ALTER TABLE diagram_timeline ADD FOREIGN KEY (person_id) REFERENCES person(id);

-- Acontecimento marcado a mao. Pertence a TIMELINE (nao ao mapa): a mesma investigacao pode
-- ter varias linhas do tempo com recortes diferentes. entity_id e opcional — evento solto
-- ("estouro da operacao") existe sem dono, e com entidade ganha o nome dela como subtitulo.
create table diagram_timeline_event (
    id VARCHAR(128) PRIMARY KEY,
    diagram_timeline_id VARCHAR(128) NOT NULL,
    entity_id VARCHAR(128) DEFAULT NULL,
    person_id VARCHAR(128) DEFAULT NULL,
    text_label VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    start_date         DATE DEFAULT NULL,
    end_date           DATE DEFAULT NULL,
    format_date        VARCHAR(255) DEFAULT 'yyyy-MM-dd',
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);
ALTER TABLE diagram_timeline_event ADD FOREIGN KEY (diagram_timeline_id) REFERENCES diagram_timeline(id);
ALTER TABLE diagram_timeline_event ADD FOREIGN KEY (entity_id) REFERENCES entity(id);
ALTER TABLE diagram_timeline_event ADD FOREIGN KEY (person_id) REFERENCES person(id);
-- A timeline sempre carrega "os eventos deste documento, em ordem": indice pelo par.
CREATE INDEX IX_diagram_timeline_event ON diagram_timeline_event (diagram_timeline_id, start_date);

-- Referencia com data = ACONTECIMENTO. A referencia ja era a fonte ("o que diz que isso
-- aconteceu"); com data ela vira tambem o fato datado que a timeline desenha. Sao as mesmas
-- tres colunas de todo o resto do schema, entao vale pontual (so start) ou periodo.
ALTER TABLE diagram_relationship_element_reference ADD COLUMN start_date  DATE DEFAULT NULL;
ALTER TABLE diagram_relationship_element_reference ADD COLUMN end_date    DATE DEFAULT NULL;
ALTER TABLE diagram_relationship_element_reference ADD COLUMN format_date VARCHAR(255) DEFAULT 'yyyy-MM-dd';

-- ==========================================================================================
-- MIGRACAO da timeline para bancos ja em producao (ex.: cyberwar). O deploy NAO altera
-- bancos existentes (ver DEPLOY.md): rodar isto a mao, uma vez, por banco.
--
--   ALTER TABLE diagram_relationship_element_reference
--       ADD COLUMN start_date  DATE DEFAULT NULL,
--       ADD COLUMN end_date    DATE DEFAULT NULL,
--       ADD COLUMN format_date VARCHAR(255) DEFAULT 'yyyy-MM-dd';
--   -- mais as duas tabelas acima (diagram_timeline e diagram_timeline_event, com as FKs
--   -- e o indice).
--
-- Sem a migracao: o load do mapa quebra no SELECT das referencias (coluna inexistente) e a
-- timeline nao abre.
-- ==========================================================================================

-- ==========================================================================================
-- MIGRACAO de 2026-10-05: a senha guardada deixa de ser a propria credencial.
--
-- O login comparava o valor recebido direto com a coluna `password`. Como o cliente manda
-- sha256(senha + salt), o conteudo da coluna ERA o segredo: quem o lesse entrava. Agora o
-- servidor guarda password_hash() e confere com password_verify().
--
-- NAO E PRECISO REDEFINIR SENHA NENHUMA, e nenhum cliente precisa ser atualizado: o
-- session.php aceita o formato antigo UMA vez e reescreve a linha no formato novo no proprio
-- login. Em uma base pequena isso basta -- a migracao acontece sozinha, conta a conta.
--
-- Para fechar de imediato (recomendado, porque enquanto houver linha no formato antigo o
-- valor dela continua valendo como credencial), rode o conversor de uma vez. Ele e PHP porque
-- password_hash nao existe em SQL:
--
--     php server/ferramentas/migrar_senhas.php <domain>
--
-- O conversor le cada linha, pula as que ja estao em bcrypt e reescreve o resto com o hash
-- dela mesma -- calculavel a partir da propria coluna, sem saber a senha de ninguem.
--
-- Depois de migrar, o hash que este arquivo publicava nas versoes anteriores deixa de ser
-- aceito como entrada.
--
-- Conferir o que falta migrar:
--   SELECT count(*) FROM person WHERE password <> '' AND password NOT LIKE '$2y$%';
-- ==========================================================================================

-- ==========================================================================================
-- MIGRACAO de 2026-10-06: marcar os paises ja semeados com o sub-tipo "country".
--
-- O Mapa Regional reconhece um pais pelo sub_etype (ver classlib/relationship/regional.py).
-- O country_seed.py passou a gravar isso, mas quem semeou ANTES tem os paises como "other"
-- sem sub-tipo, e eles nao aparecem no mapa regional.
--
-- Os paises semeados tem id = uuid5 do ISO, entao sao reconheciveis pelo FORMATO do id
-- (UUID com hifens) somado a ter bandeira em entity_face -- que e o que o seeder grava e
-- quase nada mais tem. Confira a lista ANTES de marcar:
--
--   SELECT e.id, e.text_label, se.name AS sub_tipo_hoje FROM entity e
--     INNER JOIN entity_face f ON f.entity_id = e.id
--     LEFT  JOIN sub_etype se ON se.id = e.sub_etype_id
--    WHERE e.etype = 'other' AND e.id LIKE '%-%-%-%-%';
--
-- Se a lista estiver certa:
--
--   INSERT INTO sub_etype (id, name) VALUES (MD5('country'), 'country')
--     ON DUPLICATE KEY UPDATE name = VALUES(name);
--
--   UPDATE entity e INNER JOIN entity_face f ON f.entity_id = e.id
--      SET e.sub_etype_id = MD5('country')
--    WHERE e.etype = 'other' AND e.id LIKE '%-%-%-%-%'
--      AND e.sub_etype_id IS NULL;
--
-- A guarda `sub_etype_id IS NULL` nao e detalhe: sem ela a migracao SOBRESCREVE classificacao
-- boa. No banco do dono ela pegaria a entidade "Cuba", que e a familia de RANSOMWARE Cuba com
-- sub-tipo `malware` -- o country_seed casa por nome (ele "enriquece" em vez de duplicar) e
-- pendurou a bandeira de Cuba no ransomware. Rodada com a guarda, a Cuba segue `malware`; sem
-- ela, viraria `country` e apareceria como pais no mapa regional. Rodado em 06/10/2026 no
-- CYBERWARFARE: 236 marcadas, 1 preservada.
--
-- Para desfazer (todas as marcadas tinham sub_etype_id NULL antes):
--
--   UPDATE entity e INNER JOIN entity_face f ON f.entity_id = e.id
--      SET e.sub_etype_id = NULL
--    WHERE e.etype = 'other' AND e.id LIKE '%-%-%-%-%'
--      AND e.sub_etype_id = MD5('country');
--
-- O que a migracao NAO alcanca, e e decisao de quem cuida do acervo: pais cadastrado como
-- `organization` (no banco do dono: Canada, China, France, Hong Kong, Indonesia, Pakistan,
-- Philippines, Taiwan, Turkey, United Arab Emirates e mais) e pais de id nativo (Israel). O
-- `etype = 'other'` esta no WHERE de proposito -- e ele que mantem o APT29, que tambem ganhou
-- bandeira do seeder, fora da lista.
--
-- Rodar de novo e inofensivo. Sem esta migracao nada quebra: o mapa regional apenas nao acha
-- pais nenhum, e diz isso na tela.
-- ==========================================================================================
