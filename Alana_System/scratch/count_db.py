import sqlite3
conn = sqlite3.connect('data/memory/alana_graph.db')
res = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
rel = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
print(f"Total Entidades: {res}")
print(f"Total Relacoes: {rel}")
conn.close()
