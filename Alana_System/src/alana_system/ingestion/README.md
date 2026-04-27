# 📥 Alana Ingestion System (The Factory)

Este diretório contém a "Linha de Montagem" de conhecimento da Alana. É responsável por transformar dados brutos em inteligência estruturada e vetorial.

## ⚙️ Componentes Principais

1. **`IngestionManager` (O Orquestrador)**: Gerencia o fluxo completo, garantindo que cada arquivo passe pelas etapas de extração, limpeza, chunking e indexação.
2. **`TextExtractor` (Universal)**: Engine de alta performance para PDF (PyMuPDF), DOCX, MD e TXT.
3. **`AudioTranscriber` (Faster-Whisper)**: Transforma áudio em blocos de texto temporais (páginas lógicas).
4. **`Checkpoint System`**: Integrado ao `GraphStore`, utiliza SQLite para garantir que o progresso seja salvo lote por lote.

## 🛡️ Regras de Ouro para Ingestão

1. **Sempre use Hashes**: Nunca confie apenas no nome do arquivo. Use `extractor.get_file_hash()` para validar a identidade do conteúdo.
2. **Namespace é Obrigatório**: Todo conhecimento deve pertencer a um contexto (namespace) para evitar vazamento de dados.
3. **Respeite o Hardware local**: O `max_workers` do Manager deve ser mantido baixo (2-4) para não sobrecarregar a GPU durante a execução do Ollama/Whisper.
4. **Persistência Atômica**: Sempre marque o lote como concluído (`mark_batch_complete`) *depois* de garantir que os dados chegaram ao Grafo e ao Vetor.

## 🧪 Validação
Para testar o pipeline sem gastar tokens ou processamento real:
```bash
python tests/test_ingestion_turbo.py
```
