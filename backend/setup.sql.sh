#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE TABLE IF NOT EXISTS challenges(id varchar(256), name varchar(256), description text, author text, kube json);
    CREATE TABLE IF NOT EXISTS tags(challenge_id varchar(256), name varchar(64), is_category boolean);
EOSQL


