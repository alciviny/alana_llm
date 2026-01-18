import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Chave GEMINI_API_KEY não encontrada. Verifique seu arquivo .env")
else:
    genai.configure(api_key=api_key)

    print("🔍 Modelos disponíveis para você:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"-> {m.name}")
    except Exception as e:
        print(f"❌ Ocorreu um erro ao listar os modelos: {e}")
        print("   Por favor, verifique se sua chave de API é válida e está ativa no Google AI Studio.")

