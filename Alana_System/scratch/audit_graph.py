import sqlite3
from pathlib import Path

db_path = Path("data/memory/alana_graph.db")

def audit():
    if not db_path.exists():
        print(f"Erro: Banco de dados não encontrado em {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- Auditoria de Entidades Suspeitas (Pequenas) ---")
    cursor.execute("SELECT name, type FROM entities WHERE length(name) <= 2 LIMIT 30;")
    rows = cursor.fetchall()
    for row in rows:
        print(f"[{row['type']}] {row['name']}")

    print("\n--- Auditoria de Relações Estranhas ---")
    cursor.execute("SELECT subject, relation, object FROM relations LIMIT 20;")
    rows = cursor.fetchall()
    for row in rows:
        print(f"{row['subject']} --({row['relation']})--> {row['object']}")

    conn.close()

if __name__ == "__main__":
    audit()
