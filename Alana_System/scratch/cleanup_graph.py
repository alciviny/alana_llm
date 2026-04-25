import sqlite3
from pathlib import Path

db_path = Path("data/memory/alana_graph.db")

def cleanup():
    if not db_path.exists():
        print("Banco de dados não encontrado.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Apaga entidades que são apenas números ou ruídos curtos
    # Mantemos apenas os símbolos técnicos da nossa 'whitelist'
    tech_whitelist = "('V', 'I', 'R', 'C', 'L', 'Q', 'P', 'AC', 'DC', 'Hz', 'HF', 'RF')"
    
    print("--- Removendo entidades ruidosas (numeros e letras soltas) ---")
    
    # Remove entidades com apenas dígitos
    cursor.execute("DELETE FROM entities WHERE name GLOB '[0-9]*';")
    
    # Remove entidades muito curtas que não estão na whitelist
    cursor.execute(f"DELETE FROM entities WHERE length(name) < 3 AND name NOT IN {tech_whitelist};")
    
    # Remove ruídos específicos conhecidos
    cursor.execute("DELETE FROM entities WHERE name IN ('F1', 'F2', 'F5', 'TV', 'PP', 'FF');")

    # 2. Limpa as relações que ficaram 'órfãs' (sem o sujeito ou objeto que apagamos)
    print("--- Limpando relacoes orfas ---")
    cursor.execute("""
        DELETE FROM relations 
        WHERE subject NOT IN (SELECT name FROM entities)
           OR object NOT IN (SELECT name FROM entities);
    """)

    conn.commit()
    count = cursor.rowcount
    conn.close()
    print(f"Limpeza concluida! {count} relacoes inuteis foram removidas.")

if __name__ == "__main__":
    cleanup()
