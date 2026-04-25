import os
import sys

# Adiciona src ao path para os imports funcionarem
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from alana_system.inference.llm_engine import LLMEngine
import logging

logging.basicConfig(level=logging.INFO)

def test_local_model():
    model_path = "models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
    if not os.path.exists(model_path):
        print(f"Modelo não encontrado: {model_path}")
        return
        
    print(f"Testando com o modelo: {model_path}")
    engine = LLMEngine(model_path=model_path, context_window=512)
    
    print("\nFazendo uma pergunta simples para o modelo local...")
    resposta = engine.generate_answer(
        query="Quanto é 2 + 2?",
        context_text="Você é um assistente de matemática muito inteligente."
    )
    
    print("\n=== RESPOSTA ===")
    print(resposta)

if __name__ == "__main__":
    test_local_model()
