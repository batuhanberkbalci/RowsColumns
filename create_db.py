import psycopg2

conn = psycopg2.connect("postgresql://postgres:esmail1888@localhost:5432/postgres")
conn.autocommit = True          # CREATE DATABASE cannot run inside a transaction
with conn.cursor() as cur:
    cur.execute("CREATE DATABASE workspace_booking")
conn.close()
print("Database created.")
