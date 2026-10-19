import psycopg2
conn = psycopg2.connect('postgresql://demiempresa_online_user:qPQ3Dt6qquqpOzRKESgTGf9NjefSeISK@dpg-d9uabv6417fc7383k650-a.virginia-postgres.render.com/demiempresa_online?sslmode=require')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
for table in cur.fetchall():
    print(table[0])
