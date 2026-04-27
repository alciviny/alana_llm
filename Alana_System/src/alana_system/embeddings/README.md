# 🔢 Alana Embeddings Module

Este módulo é responsável por converter linguagem natural em representações vetoriais (números) que podem ser processadas matematicamente para busca semântica.

## 🚀 Performance & Memória

- **Singleton Pattern**: O `TextEmbedder` utiliza o padrão Singleton para garantir que o modelo de 500MB seja carregado apenas uma vez na VRAM/RAM, independentemente de quantas vezes a classe seja instanciada.
- **Multilíngue**: O modelo padrão (`paraphrase-multilingual-MiniLM-L12-v2`) foi escolhido por sua excelente performance em Português e Inglês.
- **Batching**: O processamento é feito em lotes (batches) para evitar picos de consumo de memória durante a ingestão de grandes volumes de documentos.

## 🛠️ Uso Básico

```python
from alana_system.embeddings.embedder import TextEmbedder

embedder = TextEmbedder()
vector = embedder.embed_query("Qual o teorema de Pitágoras?")
```

## ⚠️ Segurança Offline
O modelo é baixado na primeira execução e cacheado localmente. Em ambientes sem internet, certifique-se de que o diretório de cache do Hugging Face (`~/.cache/huggingface`) contenha os arquivos necessários.
