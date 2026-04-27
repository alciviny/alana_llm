# 🔍 Alana Query Engine (Radar System)

Este diretório contém o motor de busca híbrida e inteligência de recuperação da Alana. É o componente responsável por transformar perguntas em contextos densos e precisos.

## 🏗️ Estrutura e Fluxo

O `QueryEngine` segue o protocolo **RAG Turbo (Retrieval-Augmented Generation)**:
1. **Embeddings**: Transforma a pergunta em um vetor numérico.
2. **Vector Search**: Recupera os documentos mais similares (Top 15).
3. **Neural Re-Ranking**: Usa um Cross-Encoder para garantir que os documentos mais relevantes subam para o topo (Top 5).
4. **Graph Deep Search**: Extrai entidades e busca conexões lógicas de 2 níveis no Grafo.
5. **Pattern Analysis**: Usa inteligência analítica para deduzir insights ocultos.

## 🛡️ Regras de Implementação (Padrão de Elite)

1. **Isolamento de Namespace**: Nunca execute uma busca sem passar o parâmetro `namespace`. O conhecimento deve ser isolado por projeto.
2. **Modelo Singleton**: Modelos de IA (Rerankers, Extratores) devem ser carregados apenas uma vez no `__init__`.
3. **Métricas de Performance**: Toda consulta deve retornar um dicionário de performance para auditoria de latência.
4. **Contexto Híbrido**: O prompt final deve ser uma composição de:
    - Insights Cognitivos
    - Conhecimento Estruturado (Grafo)
    - Trechos Originais (Vetores)

## 🧪 Como Testar
Antes de submeter qualquer mudança, valide a propagação de namespace e performance:
```bash
python tests/test_query_turbo.py
```
