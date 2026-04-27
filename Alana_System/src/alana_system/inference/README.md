# 🧠 Alana Inference Engine

Este diretório contém o núcleo de comunicação com Modelos de Linguagem de Larga Escala (LLMs).

## 🚀 Estratégia de Inferência

A Alana utiliza uma estratégia **Local-First**, priorizando o uso do **Ollama** rodando no hardware do usuário.

### Componentes:
1. **`LLMEngine`**: O motor principal. Utiliza `litellm` para abstração, mas é otimizado para o endpoint `localhost:11434` do Ollama.
2. **Streaming**: Suporte nativo para respostas em tempo real, melhorando a experiência do usuário.
3. **Resiliência**: Implementa retentativas automáticas com espera exponencial caso o modelo local falhe ou esteja sobrecarregado.

## 🛠️ Configuração

O modelo padrão é definido no arquivo `.env`:
```env
DEFAULT_MODEL=ollama/llama3.1
OLLAMA_BASE_URL=http://localhost:11434
```

## 🧪 Como Testar
Para validar a integridade da comunicação e dos mocks:
```bash
python tests/test_inference_turbo.py
```
