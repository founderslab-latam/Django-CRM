#!/bin/bash
# Runs once, on first boot with an empty data directory (Postgres'
# /docker-entrypoint-initdb.d mechanism).
#
# Creates the NON-SUPERUSER role the application connects as. A PostgreSQL
# superuser silently bypasses every Row-Level Security policy this project uses
# for tenant isolation, so the app must never connect as `postgres`. See
# docs/self-hosting/postgresql-and-rls.md.
#
# Same effect as the dev docker/postgres/init-rls-user.sql, but the role name
# and password come from the environment (.env.prod: DBUSER / DBPASSWORD)
# instead of being hard-coded.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DBUSER}') THEN
        CREATE ROLE ${DBUSER} WITH LOGIN PASSWORD '${DBPASSWORD}';
    END IF;
END
\$\$;

GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${DBUSER};
GRANT ALL ON SCHEMA public TO ${DBUSER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DBUSER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DBUSER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO ${DBUSER};
EOSQL

echo "Role ${DBUSER} is ready."
