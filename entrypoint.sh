#!/usr/bin/env bash
set -e

# Chờ Postgres sẵn sàng
echo "Waiting for Postgres at $DATABASE_URL ..."
# Trích host/port/user/db để pg_isready kiểm tra (dùng env trực tiếp nếu muốn)
DB_HOST="${DATABASE_URL##*@}"
DB_HOST="${DB_HOST%%:*}"            # sẽ sai vì DATABASE_URL dạng DSN, nên dùng nc thay thế

# Dùng nc để đợi cổng 5432 của service 'db'
until nc -z db 5432; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done

echo "Postgres is up - running migrations"
alembic upgrade head

echo "Starting Uvicorn..."
# Dev: bật --reload + host 0.0.0.0
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
