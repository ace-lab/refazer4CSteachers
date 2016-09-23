drop table if exists entries;
create table entries (
  id integer primary key autoincrement,
  title text not null,
  cluster_id integer not null,
  question_number integer not null,
  tab_id integer not null,
  'text' text not null
);
