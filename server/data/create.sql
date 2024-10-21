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
    etype VARCHAR(255) NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
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
    x INT NOT NULL, y INT NOT NULL, w INT NOT NULL, h INT NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table diagram_relationship_element_reference( 
    id VARCHAR(128) PRIMARY KEY,
    entity_id VARCHAR(128) NOT NULL,
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
    title VARCHAR(255), link1 TEXT, link2 TEXT, link3 TEXT,
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
    organization_chart_id VARCHAR(128) NOT NULL,
    organization_chart_item_parent_id VARCHAR(128) NOT NULL,
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);

create table organization_chart_item_entity( 
    id VARCHAR(128) PRIMARY KEY,
    organization_chart_item_id VARCHAR(128) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
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


