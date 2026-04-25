import time
import requests

start = time.time()
response = requests.post(
    "http://localhost:8000/generate",
    json={"query": "O que é uma base e dimensão de um espaço vetorial, e como o Teorema do Núcleo e da Imagem se aplica?"}
)
duration = time.time() - start

print(f"Tempo: {duration:.2f} segundos")
if response.status_code == 200:
    print("Resposta:")
    print(response.json().get("answer", "No answer field"))
else:
    print(f"Erro {response.status_code}: {response.text}")
