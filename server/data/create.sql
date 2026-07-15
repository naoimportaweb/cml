
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
    name varchar(255) NOT NULL
);

create table entity_image (
    id VARCHAR(128) PRIMARY KEY,
    entity_id VARCHAR(128) NOT NULL,
    path varchar(255) NOT NULL
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
    name varchar(255) NOT NULL
);

create table entity_image (
    id VARCHAR(128) PRIMARY KEY,
    entity_id VARCHAR(128) NOT NULL,
    path varchar(255) NOT NULL
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

insert into person (id, username, name, password, salt, email) values ('1', 'nao.importa.web', 'nao.importa.web', '7c61be27eec3fa7cef2e0d44d3145ea37648b0842d5574c0163b92c0bed54924', '1111', '');

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
