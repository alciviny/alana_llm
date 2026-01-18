from litellm import completion
import os
from dotenv import load_dotenv

load_dotenv()

# DEBUG: Verifica se a chave está sendo carregada do .env
print("DEBUG: Carregando a chave da API do arquivo .env...")

try:
    response = completion(
        model="gemini/gemini-2.5-flash", 
        messages=[{"role": "user", "content": "Oi! Testando o motor de 2026."}]
    )
    print("✅ Conexão OK! Resposta:", response.choices[0].message.content)
except Exception as e:
    print("❌ Erro na conexão:", e)
