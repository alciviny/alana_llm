import sqlite3
import logging
import re
import uuid
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from alana_system.preprocessing.entity_extractor import KnowledgeGraphSchema

logger = logging.getLogger("alana.memory.graph")

class GraphStore:
    """
    Motor de Armazenamento em Grafo (SQLite).
    Gerencia entidades, relacoes, aliases e jobs de ingestao com foco em integridade industrial.
    """
    def __init__(self, db_path: str = "data/memory/alana_graph.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        """Cria uma conexao robusta com timeout e modo de seguranca para Windows/Docker."""
        import time
        for attempt in range(3):
            try:
                conn = sqlite3.connect(self.db_path, timeout=60.0)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            except sqlite3.OperationalError as e:
                if "disk I/O error" in str(e).lower() and attempt < 2:
                    time.sleep(1)
                    continue
                raise

    def _init_db(self) -> None:
        """Inicializa o esquema do banco de dados industrial."""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Tabela de Entidades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    namespace TEXT DEFAULT 'global',
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, namespace)
                )
            """)
            
            # Migracao para entities: adiciona namespace e description
            try:
                cursor.execute("SELECT description FROM entities LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("🔧 Migrando entities: Adicionando coluna 'description' e 'namespace'...")
                try: cursor.execute("ALTER TABLE entities ADD COLUMN namespace TEXT DEFAULT 'global'")
                except: pass
                cursor.execute("ALTER TABLE entities ADD COLUMN description TEXT")
                conn.commit()
            # Tabela de Relacoes (Core do Grafo)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    object TEXT NOT NULL,
                    source_doc TEXT,
                    page_number INTEGER,
                    namespace TEXT DEFAULT 'global',
                    version INTEGER DEFAULT 1,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(subject, relation, object, source_doc, namespace, version)
                )
            """)
            
            # Auto-Migracao Industrial: Garante consistencia do esquema
            try:
                cursor.execute("SELECT version FROM relations LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("🔧 Migrando banco de dados: Adicionando coluna 'version'...")
                cursor.execute("ALTER TABLE relations ADD COLUMN version INTEGER DEFAULT 1")
                conn.commit()
            # Tabela de Sinônimos/Aliases
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_aliases (
                    alias TEXT PRIMARY KEY,
                    canonical_name TEXT NOT NULL,
                    FOREIGN KEY(canonical_name) REFERENCES entities(name)
                )
            """)
            # Tabela de Controle de Ingestao (Checkpoints)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING',
                    total_batches INTEGER DEFAULT 0,
                    completed_batches INTEGER DEFAULT 0,
                    error_message TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_hash, namespace)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_batches (
                    file_hash TEXT,
                    namespace TEXT,
                    batch_number INTEGER,
                    PRIMARY KEY(file_hash, namespace, batch_number)
                )
            """)
            
            # Tabela para Reconciliação Semântica (Armazena vetores de nomes de entidades)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_embeddings (
                    entity_name TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    namespace TEXT DEFAULT 'global',
                    FOREIGN KEY(entity_name) REFERENCES entities(name)
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_namespace ON relations(namespace)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_subject ON relations(subject)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_object ON relations(object)")
            conn.commit()

    def normalize_name(self, name: str) -> str:
        """Normalizacao focada em precisao tecnica."""
        name = name.strip()
        if not name: return ""
        if len(name) <= 3:
            # Preserva original para siglas (ex: GPU, VCC) ou limpa se for comum
            return name.strip() if not name.isupper() else name.upper()
        words = name.split()
        if not words: return ""
        
        normalized_words = [words[0].capitalize()]
        connectives = {"de", "da", "do", "em", "com", "para", "e", "o", "a"}
        for word in words[1:]:
            lower_w = word.lower()
            if lower_w in connectives: normalized_words.append(lower_w)
            elif word.isupper() or any(c.isdigit() for c in word): normalized_words.append(word)
            else: normalized_words.append(word.capitalize())
        return " ".join(normalized_words)

    @lru_cache(maxsize=1024)
    def _resolve_canonical_name_cached(self, name: str) -> str:
        """Versao com cache para evitar IO excessivo em loop (Ponto 4 Auditoria)."""
        normalized = self.normalize_name(name)
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT canonical_name FROM entity_aliases WHERE alias = ?", (normalized,))
                row = cursor.fetchone()
                if row: return row["canonical_name"]
                cursor.execute("SELECT name FROM entities WHERE name = ?", (normalized,))
                row = cursor.fetchone()
                return row["name"] if row else normalized
        except Exception:
            return normalized

    def _resolve_canonical_name(self, cursor, name: str) -> str:
        """Resolve alias usando cursor existente (dentro de transacao)."""
        normalized = self.normalize_name(name)
        cursor.execute("SELECT canonical_name FROM entity_aliases WHERE alias = ?", (normalized,))
        row = cursor.fetchone()
        if row: return row["canonical_name"]
        cursor.execute("SELECT name FROM entities WHERE name = ?", (normalized,))
        row = cursor.fetchone()
        return row["name"] if row else normalized

    def add_knowledge(self, graph: KnowledgeGraphSchema, source_doc: str, page_number: int, namespace: str = "global") -> None:
        """Persiste um grafo completo extraído por IA."""
        if not graph: return
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                for entity in (graph.entities or []):
                    canonical = self._resolve_canonical_name(cursor, entity.name)
                    # Fusao Inteligente: Se ja existe, tenta mesclar metadados (Ponto Critico Auditoria)
                    cursor.execute("SELECT description, type FROM entities WHERE name = ? AND namespace = ?", (canonical, namespace))
                    existing = cursor.fetchone()
                    
                    if existing:
                        new_desc = entity.description if entity.description else ""
                        old_desc = existing["description"] if existing["description"] else ""
                        # Mescla descricoes se forem diferentes e relevantes
                        if new_desc and new_desc not in old_desc:
                            merged = f"{old_desc} | {new_desc}".strip(" | ")
                            cursor.execute("UPDATE entities SET description = ? WHERE name = ? AND namespace = ?", (merged, canonical, namespace))
                    else:
                        cursor.execute("INSERT INTO entities (name, type, description, namespace) VALUES (?, ?, ?, ?)", 
                                     (canonical, entity.type, entity.description, namespace))
                
                for rel in (graph.relations or []):
                    subj = self._resolve_canonical_name(cursor, rel.subject)
                    obj = self._resolve_canonical_name(cursor, rel.object)
                    # Garante existencia com namespace
                    cursor.execute("INSERT OR IGNORE INTO entities (name, type, namespace) VALUES (?, ?, ?)", (subj, "Conceito", namespace))
                    cursor.execute("INSERT OR IGNORE INTO entities (name, type, namespace) VALUES (?, ?, ?)", (obj, "Conceito", namespace))
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO relations (subject, relation, object, source_doc, page_number, namespace, version)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (subj, rel.predicate, obj, source_doc, page_number, namespace, 1))
                conn.commit()
        except Exception as e:
            logger.error(f"Erro ao persistir conhecimento: {e}")

    def add_fact(self, subject: str, relation: str, object_name: str, source: str = "AGENT_DISCOVERY", namespace: str = "global") -> bool:
        """Adiciona um fato unico (Agent Discoveries)."""
        try:
            s_norm = self.normalize_name(subject)
            o_norm = self.normalize_name(object_name)
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO entities (name, type) VALUES (?, ?)", (s_norm, "Entity"))
                cursor.execute("INSERT OR IGNORE INTO entities (name, type) VALUES (?, ?)", (o_norm, "Entity"))
                cursor.execute("""
                    INSERT OR IGNORE INTO relations (subject, relation, object, source_doc, page_number, namespace)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (s_norm, relation.lower(), o_norm, source, 0, namespace))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar fato: {e}")
            return False

    def query_subgraph(self, entity_names: List[str], limit: int = 50, namespace: str = "global") -> List[Dict]:
        """Consulta vizinhanca de 2-HOPS filtrada por namespace."""
        if not entity_names: return []
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                placeholders = ", ".join(["?"] * len(entity_names))
                query = f"""
                    SELECT DISTINCT subject, relation, object, source_doc, page_number
                    FROM relations WHERE (subject IN ({placeholders}) OR object IN ({placeholders})) AND namespace = ?
                    LIMIT ?
                """
                cursor.execute(query, (*entity_names, *entity_names, namespace, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    def query_subgraph_by_namespace(self, namespace: str, limit: int = 150, version: int = 1) -> List[Dict]:
        """Consulta relacoes e tipos em um unico JOIN (Otimizado para Dashboard) com suporte temporal."""
        query = """
            SELECT r.subject, r.relation, r.object, 
                   e1.type as s_type, e1.description as s_desc,
                   e2.type as o_type, e2.description as o_desc
            FROM relations r
            LEFT JOIN entities e1 ON r.subject = e1.name AND r.namespace = e1.namespace
            LEFT JOIN entities e2 ON r.object = e2.name AND r.namespace = e2.namespace
            WHERE r.namespace = ? AND r.version = ?
            ORDER BY r.timestamp DESC
            LIMIT ?
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (namespace, version, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Erro no export de subgrafo: {e}")
            return []

    def top_hubs(self, limit: int = 10, namespace: str = "global") -> List[Dict]:
        """Retorna as entidades mais conectadas do namespace."""
        query = """
            SELECT entity, COUNT(*) as total FROM (
                SELECT subject as entity FROM relations WHERE namespace = ?
                UNION ALL
                SELECT object as entity FROM relations WHERE namespace = ?
            ) GROUP BY entity ORDER BY total DESC LIMIT ?
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (namespace, namespace, limit))
            return [dict(row) for row in cursor.fetchall()]

    # --- Gestao de Jobs (Checkpoints) ---
    def register_ingestion_job(self, file_hash: str, filename: str, total_batches: int, namespace: str = "global"):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO ingestion_jobs (file_hash, filename, total_batches, namespace, status, completed_batches, updated_at)
                VALUES (?, ?, ?, ?, 'PENDING', 0, CURRENT_TIMESTAMP)
                ON CONFLICT(file_hash, namespace) DO UPDATE SET status = 'PENDING', updated_at = CURRENT_TIMESTAMP
            """, (file_hash, filename, total_batches, namespace))
            conn.commit()

    def mark_batch_complete(self, file_hash: str, namespace: str, batch_number: int):
        with self._connect() as conn:
            conn.execute("INSERT OR IGNORE INTO processed_batches (file_hash, namespace, batch_number) VALUES (?, ?, ?)", (file_hash, namespace, batch_number))
            conn.execute("""
                UPDATE ingestion_jobs SET completed_batches = (SELECT COUNT(*) FROM processed_batches WHERE file_hash = ? AND namespace = ?),
                status = 'PROCESSING', updated_at = CURRENT_TIMESTAMP WHERE file_hash = ? AND namespace = ?
            """, (file_hash, namespace, file_hash, namespace))
            conn.commit()

    def get_processed_batches(self, file_hash: str, namespace: str) -> List[int]:
        with self._connect() as conn:
            rows = conn.execute("SELECT batch_number FROM processed_batches WHERE file_hash = ? AND namespace = ?", (file_hash, namespace)).fetchall()
            return [row["batch_number"] for row in rows]

    def get_all_jobs(self) -> List[Dict]:
        with self._connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM ingestion_jobs ORDER BY updated_at DESC").fetchall()]

    def update_job_status(self, file_hash: str, namespace: str, status: str, error_message: str = None) -> None:
        """Atualiza o status de um job de ingestão (PENDING, PROCESSING, COMPLETED, FAILED)."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE ingestion_jobs
                SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE file_hash = ? AND namespace = ?
                """,
                (status, error_message, file_hash, namespace),
            )
            conn.commit()

    # --- Reconciliação Semântica (Ponto 3 Auditoria) ---
    def save_entity_embedding(self, name: str, embedding_vector: List[float], namespace: str = "global"):
        import json
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO entity_embeddings (entity_name, embedding, namespace) VALUES (?, ?, ?)",
                (name, json.dumps(embedding_vector), namespace)
            )
            conn.commit()

    def get_all_entity_embeddings(self, namespace: str = "global") -> Dict[str, List[float]]:
        import json
        with self._connect() as conn:
            rows = conn.execute("SELECT entity_name, embedding FROM entity_embeddings WHERE namespace = ?", (namespace,)).fetchall()
            return {row["entity_name"]: json.loads(row["embedding"]) for row in rows}

    def add_alias(self, alias: str, canonical: str):
        with self._connect() as conn:
            conn.execute("INSERT OR IGNORE INTO entity_aliases (alias, canonical_name) VALUES (?, ?)", (alias, canonical))
            conn.commit()

    def get_all_edges(self, namespace: str = "global") -> List[tuple]:
        """
        Retorna triplos filtrados por namespace (Ponto 1 Auditoria).
        Garante isolamento e evita carregamento total desnecessario.
        """
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT subject, relation, object FROM relations WHERE namespace = ?",
                    (namespace,)
                ).fetchall()
                return [(r["subject"], r["relation"], r["object"]) for r in rows]
        except Exception as e:
            logger.error(f"Erro ao recuperar arestas do grafo: {e}")
            return []
