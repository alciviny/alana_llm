import sqlite3
import logging
import re
from typing import List, Dict, Optional
from pathlib import Path

from alana_system.preprocessing.entity_extractor import KnowledgeGraphSchema

logger = logging.getLogger(__name__)

class GraphStore:
    def __init__(self, db_path: str = "data/memory/alana_graph.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Cria tabelas e índices se não existirem."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    object TEXT NOT NULL,
                    source_doc TEXT,
                    page_number INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(subject, relation, object, source_doc)
                )
            """)
            
            # Nova tabela para resolver sinônimos (ex: "EUA" -> "Estados Unidos")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_aliases (
                    alias TEXT PRIMARY KEY,
                    canonical_name TEXT NOT NULL,
                    FOREIGN KEY(canonical_name) REFERENCES entities(name)
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_subject ON relations(subject)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_object ON relations(object)")
            conn.commit()

    # -------------------------------------------------
    # Normalização e Deduplicação
    # -------------------------------------------------

    def _normalize_name(self, name: str) -> str:
        """Normalização mais conservadora para preservar legibilidade."""
        return name.strip().title()

    def _resolve_canonical_name(self, cursor, name: str) -> str:
        """Busca o nome canônico através de aliases ou normalização."""
        normalized = self._normalize_name(name)
        
        # 1. Tenta buscar na tabela de aliases
        cursor.execute("SELECT canonical_name FROM entity_aliases WHERE alias = ?", (normalized,))
        row = cursor.fetchone()
        if row:
            return row["canonical_name"]
            
        # 2. Tenta buscar se o nome já existe na tabela de entidades (case-sensitive)
        cursor.execute("SELECT name FROM entities WHERE name = ?", (normalized,))
        row = cursor.fetchone()
        if row:
            return row["name"]
        
        # 3. Tenta uma busca mais flexível (case-insensitive e sem espaços)
        no_space_normalized = normalized.replace(" ", "")
        cursor.execute(
            "SELECT name FROM entities WHERE REPLACE(name, ' ', '') = ? COLLATE NOCASE", 
            (no_space_normalized,)
        )
        row = cursor.fetchone()
        if row:
            # Encontrou! Adiciona um alias para acelerar buscas futuras.
            canonical_name = row["name"]
            cursor.execute(
                "INSERT OR IGNORE INTO entity_aliases (alias, canonical_name) VALUES (?, ?)",
                (normalized, canonical_name)
            )
            return canonical_name
            
        return normalized

    def add_knowledge(
        self,
        graph: KnowledgeGraphSchema,
        source_doc: str,
        page_number: int
    ) -> None:
        """Persiste entidades e relações com deduplicação otimizada."""
        if not graph or (not graph.entities and not graph.relations):
            return

        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                resolved_map: Dict[str, str] = {}

                # 1. Processar Entidades
                for entity in graph.entities:
                    canonical = self._resolve_canonical_name(cursor, entity.name)
                    cursor.execute(
                        "INSERT OR IGNORE INTO entities (name, type) VALUES (?, ?)",
                        (canonical, entity.type)
                    )
                    resolved_map[entity.name] = canonical

                # 2. Processar Relações com nomes resolvidos
                for rel in graph.relations:
                    subj = resolved_map.get(rel.subject, self._resolve_canonical_name(cursor, rel.subject))
                    obj = resolved_map.get(rel.object, self._resolve_canonical_name(cursor, rel.object))
                    cursor.execute(
                        """INSERT OR IGNORE INTO relations 
                           (subject, relation, object, source_doc, page_number)
                           VALUES (?, ?, ?, ?, ?)""",
                        (subj, rel.predicate, obj, source_doc, page_number)
                    )
                conn.commit()
                logger.debug(f"Grafo persistido | doc={source_doc} page={page_number}")
        except sqlite3.Error:
            logger.exception("Erro ao persistir conhecimento no GraphStore")

    # -------------------------------------------------
    # Consulta de subgrafo
    # -------------------------------------------------

    def query_subgraph(
        self,
        entity_names: List[str],
        limit: int = 20,
        allowed_relations: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Recupera a vizinhança local do grafo a partir de entidades semente."""
        if not entity_names:
            return []

        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Prepara placeholders para as entidades (subject ou object)
                placeholders = ", ".join(["?"] * len(entity_names))
                params = entity_names + entity_names # Duplicado para Subject e Object
                
                query = f"""
                    SELECT subject, relation, object, source_doc, page_number
                    FROM relations
                    WHERE (subject IN ({placeholders}) OR object IN ({placeholders}))
                """

                # Filtro opcional por tipos de relações
                if allowed_relations:
                    rel_placeholders = ", ".join(["?"] * len(allowed_relations))
                    query += f" AND relation IN ({rel_placeholders})"
                    params.extend(allowed_relations)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            logger.exception("Erro ao consultar subgrafo")
            return []

    def count_entities(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]