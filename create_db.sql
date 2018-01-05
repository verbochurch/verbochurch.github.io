drop table if exists member;
create table member (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name TEXT,
  last_name TEXT,
  email TEXT UNIQUE,
  phone_number TEXT,
  gender TEXT,
  birthday TEXT,
  baptism_status BOOLEAN,
  marital_status BOOLEAN,
  join_date TEXT,
  is_active BOOLEAN,
  foreign key (id) REFERENCES attendance (member_id),
  foreign key (id) REFERENCES homegroup_member (member_id),
  foreign key (email) REFERENCES user(email)
);

drop table if exists user;
create table user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE,
  password TEXT,
  role_id INTEGER,
  foreign key (id) REFERENCES homegroup_leader (user_id)
);
drop table if exists role;
create table role (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role TEXT,
  FOREIGN KEY (id) references user(role_id)
);




drop table if exists homegroup;
create table homegroup (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  location TEXT,
  description TEXT,
  latitude REAL,
  longitude REAL,
  is_active BOOLEAN,

  foreign key (id) REFERENCES homegroup_member (homegroup_id),
  foreign key (id) REFERENCES homegroup_leader (homegroup_id)
);

drop table if exists homegroup_leader;
create table homegroup_leader (
  user_id,
  homegroup_id,
  PRIMARY KEY (user_id, homegroup_id)
);


drop table if exists homegroup_member;
create table homegroup_member (
  homegroup_id,
  member_id,
  is_active BOOLEAN,
  PRIMARY KEY (homegroup_id, member_id)
);



drop table if exists meeting;
create table meeting (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT,
  time TEXT,
  foreign key (id) REFERENCES attendance (meeting_id)

);
drop table if exists attendance;
CREATE TABLE attendance (
  homegroup_id INTEGER,
  member_id INTEGER,
  meeting_id INTEGER,
  attendance BOOLEAN,
  PRIMARY KEY(homegroup_id, member_id, meeting_id)
);
