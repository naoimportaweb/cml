

create table person(
    id VARCHAR(128) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL
);

create table diagram_relationship (
    id VARCHAR(128) PRIMARY KEY,
    person_id VARCHAR(128) NOT NULL,
    keyword VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL
);

create table entity (
    id VARCHAR(128) PRIMARY KEY,
    text_label VARCHAR(255) NOT NULL,
    description TEXT,
    etype VARCHAR(255) NOT NULL
);

create table diagram_relationship_element(
    id VARCHAR(128) PRIMARY KEY,
    diagram_relationship_id VARCHAR(128) NOT NULL,
    entity_id  VARCHAR(128) NOT NULL,
    x INT NOT NULL, y INT NOT NULL, w INT NOT NULL, h INT NOT NULL
);

create table diagram_relationship_element_reference( 
    id VARCHAR(128) PRIMARY KEY,
    entity_id VARCHAR(128) NOT NULL,
    title VARCHAR(255), link1 TEXT, link2 TEXT, link3 TEXT
);

create table diagram_relationship_link(
    id VARCHAR(128) PRIMARY KEY,
    diagram_relationship_element_id VARCHAR(128) NOT NULL,
    ltype int NOT NULL
);

ALTER TABLE diagram_relationship ADD FOREIGN KEY (person_id) REFERENCES person(id);
ALTER TABLE diagram_relationship_element ADD FOREIGN KEY (entity_id) REFERENCES entity(id);
ALTER TABLE diagram_relationship_element ADD FOREIGN KEY (diagram_relationship_id) REFERENCES diagram_relationship(id);
ALTER TABLE diagram_relationship_element_reference ADD FOREIGN KEY (entity_id) REFERENCES entity(id);
ALTER TABLE diagram_relationship_link ADD FOREIGN KEY (diagram_relationship_element_id) REFERENCES diagram_relationship_element(id);

insert into person (id, username, name, password, salt) values ('1', 'admin', 'admin', '', '');


drop table diagram_relationship_link;
drop table diagram_relationship_element_reference;
drop table diagram_relationship_element;
drop table entity;
drop table diagram_relationship;

