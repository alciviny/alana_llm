import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bridge import app

client = TestClient(app)

def run_ingestion_test():
    print("\n--- Teste 4: Ingestão de PDF via API (/process_document) ---")
    pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'dummy.pdf'))
    
    payload = {
        "path": pdf_path,
        "type": "PDF"
    }
    
    print(f"Enviando documento para ingestão: {pdf_path}")
    response = client.post("/process_document", json=payload)
    
    if response.status_code == 200:
        print("[OK] Endpoint /process_document concluiu com sucesso!")
        print(f"Resposta: {response.json()}")
    else:
        print(f"[ERROR] Erro na ingestão: Status {response.status_code}")
        try:
            print(response.json())
        except:
            print(response.text)

if __name__ == "__main__":
    run_ingestion_test()
