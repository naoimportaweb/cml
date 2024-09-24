# --------------- INSTALAÇAO -------------------------------------

create table person(
    id VARCHAR(128) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
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
    etype VARCHAR(255) NOT NULL,
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


# --------------------------- LIMPANDO -------------------------

insert into person (id, username, name, password, salt) values ('1', 'nao.importa.web', 'nao.importa.web', '7c61be27eec3fa7cef2e0d44d3145ea37648b0842d5574c0163b92c0bed54924', '1111');

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
drop table entity;
drop table diagram_relationship;
drop table person_sesion;
drop table person_enter;
drop table person;




# ------------- HOMOLOGAÇAO -------------------------------

