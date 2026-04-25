# 📋 Lista de Tarefas: Refatoração Alana System

## 🔴 Fase 1: Estabilidade e Core (Urgente) [CONCLUÍDA]
- [x] **Ajustar Concorrência SQLite:**
    - [x] Ativar `PRAGMA journal_mode=WAL;` no `GraphStore`.
    - [x] Implementar retry-logic para escritas no banco de dados.
- [x] **Corrigir Gestão de Contexto:**
    - [x] Integrar `tiktoken` no `LLMEngine`.
    - [x] Substituir o slicing de caracteres por contagem de tokens real.
- [x] **Garantir Singletons:**
    - [x] Verificar se os modelos de IA (Whisper, Embeddings) estão sendo carregados apenas uma vez no startup do bridge.

## 🟡 Fase 2: Arquitetura (Organização) [CONCLUÍDA]
- [x] **Modularizar `bridge.py`:**
    - [x] Criar `src/alana_system/api/routes/`.
    - [x] Mover rotas de IoT para `src/alana_system/api/routes/iot.py`.
    - [x] Mover rotas de Chat e Admin para módulos específicos.
- [x] **Melhorar Orquestrador Go:**
    - [x] Substituir `log.Fatalf` por tratamento de erro resiliente e retries.
    - [x] Adicionar suporte a variáveis de ambiente para todos os timeouts.
- [x] **Otimizar Lógica de Grafo (Mastery):**
    - [x] Implementar inferência transitiva via SQL (Auto-Joins).
    - [x] Implementar Deep Search de 2-Hops nativo no banco.

## 🟢 Fase 3: Aesthetics e UX (Visual) [CONCLUÍDA]
- [x] **Upgrade no CSS do Frontend:**
    - [x] Implementar design minimalista e industrial (Dark Mode Profundo).
    - [x] Remover emojis e elementos visuais distractivos.
    - [x] Adicionar tipografia de alta performance (Inter / Mono).

## ⚪ Fase 4: Documentação e Manutenção
- [ ] **Atualizar README:** Corrigir a árvore de diretórios e instruções de instalação.
- [ ] **Logs Estruturados:** Garantir que todos os componentes usem o logger unificado.
