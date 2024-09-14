

create table person(
    id VARCHAR(128) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL
);

create table diagram_relationship (
    id VARCHAR(128) PRIMARY KEY,
    person_id VARCHAR(128),
    keyword VARCHAR(255),
    name VARCHAR(255) NOT NULL
);


ALTER TABLE diagram_relationship ADD FOREIGN KEY (person_id) REFERENCES person(id);


