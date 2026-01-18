import sqlite3
import logging
import re
from typing import List, Dict, Optional
from pathlib import Path

from alana_system.preprocessing.entity_extractor import KnowledgeGraph

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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_subject ON relations(subject)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_object ON relations(object)")
            conn.commit()

    # -------------------------------------------------
    # Normalização e Deduplicação
    # -------------------------------------------------

    def _normalize_name(self, name: str) -> str:
        """Normalização agressiva para deduplicação lexical."""
        return re.sub(r"[^a-zA-Z0-9]", "", name).lower()

    def add_knowledge(
        self,
        graph: KnowledgeGraph,
        source_doc: str,
        page_number: int
    ) -> None:
        """Persiste entidades e relações com deduplicação otimizada em memória."""
        if not graph or (not graph.entities and not graph.relations):
            return

        try:
            with self._connect() as conn:
                cursor = conn.cursor()

                # 1. Cache de entidades existentes para evitar múltiplas queries
                cursor.execute("SELECT name FROM entities")
                existing_map = {self._normalize_name(row["name"]): row["name"] for row in cursor.fetchall()}
                resolved_map: Dict[str, str] = {}

                # 2. Processar Entidades
                for entity in graph.entities:
                    norm_name = self._normalize_name(entity.name)
                    if norm_name in existing_map:
                        resolved_map[entity.name] = existing_map[norm_name]
                    else:
                        cursor.execute(
                            "INSERT OR IGNORE INTO entities (name, type) VALUES (?, ?)",
                            (entity.name, entity.type)
                        )
                        existing_map[norm_name] = entity.name
                        resolved_map[entity.name] = entity.name

                # 3. Processar Relações com nomes resolvidos
                for rel in graph.relations:
                    subj = resolved_map.get(rel.subject, rel.subject)
                    obj = resolved_map.get(rel.object, rel.object)
                    cursor.execute(
                        """INSERT OR IGNORE INTO relations 
                           (subject, relation, object, source_doc, page_number)
                           VALUES (?, ?, ?, ?, ?)""",
                        (subj, rel.relation, obj, source_doc, page_number)
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