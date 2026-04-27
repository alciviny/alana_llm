# 📡 Alana API System

Este diretório contém a interface de comunicação externa da Alana, construída com **FastAPI**.

## 🏗️ Arquitetura das Rotas

As rotas são modulares e organizadas por "departamentos":
- **`/chat`**: Interface de conversação direta.
- **`/ingestion`**: Processamento industrial de documentos (PDF, Áudio, Notas).
- **`/agent`**: Comunicação em tempo real via WebSockets para o Agente Autônomo.
- **`/admin`**: Gestão do sistema e monitoramento de saúde.
- **`/iot`**: Integração com dispositivos externos.

## 🚀 Padrões de Desenvolvimento

1. **Processamento Assíncrono**: Tarefas pesadas (como ingestão) utilizam `BackgroundTasks` para evitar timeouts na interface.
2. **Injeção de Dependência**: Motores como `LLMEngine` e `QueryEngine` são injetados via `app.state`, garantindo eficiência de memória.
3. **CORS**: Habilitado por padrão para permitir conexões de diferentes origens durante o desenvolvimento.

## 🛠️ Como Iniciar
O servidor principal é o `bridge.py` na raiz do projeto:
```bash
python bridge.py
```
Acesse a documentação interativa em: `http://localhost:8000/docs`
