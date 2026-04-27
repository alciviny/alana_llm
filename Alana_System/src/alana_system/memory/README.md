# 🧠 Alana Memory System

Este diretório contém a infraestrutura de armazenamento e inteligência de longo prazo da Alana.

## 🗄️ Estrutura de Armazenamento

1. **`GraphStore` (SQLite)**: Armazena o Grafo de Conhecimento (Entidades e Relações). É a fonte da verdade para fatos estruturados.
2. **`VectorStore` (Qdrant)**: Armazena memórias semânticas (embeddings). Permite que a Alana encontre informações por "sentido" e não apenas por palavras exatas.
3. **`ExperienceStore` (Híbrido)**: Armazena o histórico de missões e estratégias do agente, permitindo que ele aprenda com o passado.
4. **`Intelligence`**: Motor analítico que processa padrões e gera insights sobre os dados armazenados.

## 🛡️ Diretrizes de Segurança

- **Isolamento por Namespace**: Todo dado persistido deve incluir um `namespace`. Nunca realize buscas ou inserções sem especificar o contexto do projeto.
- **Idempotência**: Utilize hashes de conteúdo para evitar a duplicação de dados idênticos.
- **Integridade**: Modificações no esquema do banco de dados devem ser refletidas nos métodos de migração do `GraphStore`.

## 🧪 Verificação
Para validar o isolamento e a integridade da memória:
```bash
python tests/test_memory_turbo.py
```
