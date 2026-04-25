import logging
from litellm import completion

logging.basicConfig(level=logging.INFO)

def testar_ollama():
    print("Iniciando teste de comunicação com o Ollama...")
    
    # O litellm só precisa saber que a palavra mágica é 'ollama/' 
    # seguida do nome do modelo que você baixou.
    nome_do_modelo = "ollama/llama3.1"
    
    mensagens = [
        {"role": "system", "content": "Você é um assistente divertido e conciso."},
        {"role": "user", "content": "Me explique o que é um Banco de Dados usando a analogia de uma Biblioteca."}
    ]
    
    try:
        print(f"\nFazendo a pergunta para o modelo {nome_do_modelo}...")
        
        # A mágica acontece aqui: uma única linha de código!
        resposta = completion(
            model=nome_do_modelo,
            messages=mensagens
        )
        
        # Extraindo o texto da resposta
        texto = resposta.choices[0].message.content.strip()
        
        print("\n=== RESPOSTA DO OLLAMA ===")
        print(texto)
        print("==========================\n")
        print("Sucesso! O Ollama está integrado perfeitamente!")
        
    except Exception as e:
        print(f"\nOpa! Deu erro: {e}")
        print("Verifique se você já baixou o modelo rodando 'ollama pull llama3.1' no terminal.")

if __name__ == "__main__":
    testar_ollama()
