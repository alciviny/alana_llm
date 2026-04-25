import requests
import time
import sys
import os

def check_step(name, condition, success_msg, fail_msg):
    print(f"[*] Verificando: {name}...", end=" ", flush=True)
    if condition:
        print(f"[\033[92mOK\033[0m] - {success_msg}")
        return True
    else:
        print(f"[\033[91mFALHA\033[0m] - {fail_msg}")
        return False

def validate():
    print("="*50)
    print("   ALANA SYSTEM - DIAGNÓSTICO DE PRODUÇÃO")
    print("="*50)
    
    # 1. Verificar se a API está online
    try:
        res = requests.get("http://localhost:8000/health", timeout=10)
        health_data = res.json()
        check_step("API Health", res.status_code == 200, 
                   f"Online (Versão: {health_data.get('version', 'N/A')})", 
                   "API offline ou inacessível.")
    except Exception as e:
        check_step("API Health", False, "", f"Erro de conexão: {e}")
        return

    # 2. Verificar GPU no Sidecar
    try:
        # Vamos usar um endpoint que nos diga se o torch vê a GPU
        res = requests.get("http://localhost:8000/admin/status", timeout=10)
        status = res.json()
        gpu_active = status.get("gpu_available", False)
        device = status.get("device", "cpu")
        check_step("Aceleração GPU", gpu_active, 
                   f"Ativa! Usando {device.upper()}", 
                   "Inativa. Rodando em CPU (Mais lento).")
    except:
        print("[!] Endpoint /admin/status não disponível, verificando logs...")

    # 3. Verificar Qdrant
    try:
        res = requests.get("http://localhost:6333/health", timeout=5)
        check_step("Banco de Vetores", res.status_code == 200, 
                   "Qdrant está respondendo.", "Qdrant offline.")
    except:
        check_step("Banco de Vetores", False, "", "Falha ao conectar no Qdrant.")

    # 4. Teste de Inferência de Grafos
    try:
        # Tenta uma busca simples para ver se o grafo responde
        res = requests.post("http://localhost:8000/chat", 
                           json={"message": "teste de sistema", "stream": False}, 
                           timeout=15)
        check_step("Motor de RAG", res.status_code == 200, 
                   "Pipeline de busca funcional.", "Erro no processamento da busca.")
    except:
        check_step("Motor de RAG", False, "", "Timeout ou erro no GraphRAG.")

    print("="*50)
    print("DICA: Se a GPU estiver inativa, verifique se o 'NVIDIA Container Toolkit'")
    print("está instalado e se você rodou 'docker-compose up --build'.")
    print("="*50)

if __name__ == "__main__":
    validate()
