# --------------- INSTALAÇAO -------------------------------------

create table person(
    id VARCHAR(128) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
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
    entity_id VARCHAR(128) NOT NULL
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
    creation_time      DATETIME DEFAULT   CURRENT_TIMESTAMP,
    modification_time  DATETIME ON UPDATE CURRENT_TIMESTAMP
);





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

# --------------------------- LIMPANDO -------------------------

insert into person (id, username, name, password, salt) values ('1', 'nao.importa.web', 'nao.importa.web', '7c61be27eec3fa7cef2e0d44d3145ea37648b0842d5574c0163b92c0bed54924', '1111');
INSERT INTO person_enter(id, key_enter) values("c32648a2-a451-4571-810c-de3d6b61941c","c32648a2-a451-4571-810c-de3d6b61941c");
INSERT INTO person_enter(id, key_enter) values("89bb1f15-9446-409d-8ef0-863f67c23437","89bb1f15-9446-409d-8ef0-863f67c23437");
INSERT INTO person_enter(id, key_enter) values("38b196aa-c5bc-48be-a5b5-06960c10f82b","38b196aa-c5bc-48be-a5b5-06960c10f82b");
INSERT INTO person_enter(id, key_enter) values("058641b1-09db-4a8d-b6f0-f33c6090caea","058641b1-09db-4a8d-b6f0-f33c6090caea");
INSERT INTO person_enter(id, key_enter) values("0ba307ff-8f9a-47a0-a456-6ea5d8df2aa8","0ba307ff-8f9a-47a0-a456-6ea5d8df2aa8");
INSERT INTO person_enter(id, key_enter) values("3302c9d3-8d7c-4d23-a212-fb0272725a08","3302c9d3-8d7c-4d23-a212-fb0272725a08");
INSERT INTO person_enter(id, key_enter) values("672ed8cf-0bb4-4955-8de7-0a90abb17051","672ed8cf-0bb4-4955-8de7-0a90abb17051");
INSERT INTO person_enter(id, key_enter) values("9f50321e-3aa7-447c-a800-0648287240df","9f50321e-3aa7-447c-a800-0648287240df");
INSERT INTO person_enter(id, key_enter) values("93039e72-db3f-4e74-a7e5-e787fd89b74e","93039e72-db3f-4e74-a7e5-e787fd89b74e");
INSERT INTO person_enter(id, key_enter) values("a4545eb3-1577-47fc-b01c-9829b1ce4f8d","a4545eb3-1577-47fc-b01c-9829b1ce4f8d");
INSERT INTO person_enter(id, key_enter) values("0d045974-afc7-4699-b116-91672117d517","0d045974-afc7-4699-b116-91672117d517");

INSERT INTO classification(id, text_label) values('1', "Posicionamento Político");
INSERT INTO classification_item(id, classification_id, text_label) values('1', '1', 'Extrema esquerda');
INSERT INTO classification_item(id, classification_id, text_label) values('2', '1', 'Esquerda moderada');
INSERT INTO classification_item(id, classification_id, text_label) values('3', '1', 'Neutro');
INSERT INTO classification_item(id, classification_id, text_label) values('4', '1', 'Direita moderada');
INSERT INTO classification_item(id, classification_id, text_label) values('5', '1', 'Extrema direita');


delete from diagram_relationship_link;
delete from diagram_relationship_element_reference;
delete from diagram_relationship_element;
delete from entity;
delete from diagram_relationship;

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
drop table person;




# ------------- HOMOLOGAÇAO -------------------------------
