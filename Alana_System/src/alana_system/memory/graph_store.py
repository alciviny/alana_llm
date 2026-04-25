import sqlite3
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from alana_system.preprocessing.entity_extractor import KnowledgeGraphSchema

logger = logging.getLogger(__name__)

class GraphStore:
    def __init__(self, db_path: str = "data/memory/alana_graph.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        # Timeout de 20 segundos para aguardar locks serem liberados
        # Timeout de 60 segundos para evitar I/O errors no Windows/Docker
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.row_factory = sqlite3.Row
        
        # Ativa o modo WAL (Write-Ahead Logging) para alta concorrência
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;") # Otimiza performance mantendo segurança
        
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
        """Normalização focada em preservar a precisão técnica e linguística."""
        name = name.strip()
        if not name: return ""
        
        # 1. Preservação de Siglas Curtas (V, I, R, AC, DC, LLM)
        if len(name) <= 3 or name.isupper():
            return name.upper()
            
        # 2. Capitalização Inteligente (evita "Lei De Ohm")
        words = name.split()
        if not words: return ""
        
        normalized_words = [words[0].capitalize()]
        connectives = {"de", "da", "do", "em", "com", "para", "e", "o", "a"}
        
        for word in words[1:]:
            lower_word = word.lower()
            if lower_word in connectives:
                normalized_words.append(lower_word)
            elif word.isupper() or (any(c.isdigit() for c in word)):
                # Preserva palavras que já estão em caixa alta ou contém números (ex: Llama3)
                normalized_words.append(word)
            else:
                normalized_words.append(word.capitalize())
                
        return " ".join(normalized_words)

    def _resolve_canonical_name(self, cursor, name: str) -> str:
        """
        Busca o nome canônico. 
        PRECISÃO TÉCNICA: Removemos a busca por 'LIKE' que destruía conceitos específicos.
        """
        normalized = self._normalize_name(name)
        
        # 1. Busca Direta por Alias
        cursor.execute("SELECT canonical_name FROM entity_aliases WHERE alias = ?", (normalized,))
        row = cursor.fetchone()
        if row: return row["canonical_name"]
            
        # 2. Busca Direta por Nome Exato
        cursor.execute("SELECT name FROM entities WHERE name = ?", (normalized,))
        row = cursor.fetchone()
        if row: return row["name"]
        
        # Nota: Removemos a busca por similaridade (LIKE) para evitar que "Matriz Identidade" 
        # seja fundida erroneamente com "Matriz". Precisamos de precisão industrial.
            
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
                    
                    # GARANTIA DE DENSIDADE: Insere sujeito e objeto como entidades se não existirem
                    # (Fallback caso a IA tenha sido preguiçosa na lista de entidades)
                    cursor.execute("INSERT OR IGNORE INTO entities (name, type) VALUES (?, ?)", (subj, "Conceito"))
                    cursor.execute("INSERT OR IGNORE INTO entities (name, type) VALUES (?, ?)", (obj, "Conceito"))

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

    def infer_transitive_relations(self, max_hops: int = 2) -> int:
        """
        Infere relações transitivas (A -> B -> C => A -> C) usando SQL puro.
        Muito mais rápido que processamento em Python para volumes massivos.
        """
        query = """
            INSERT OR IGNORE INTO relations (subject, relation, object, source_doc, page_number)
            SELECT DISTINCT r1.subject, 'inferred_transitive', r2.object, 'sql_inference', 0
            FROM relations r1
            JOIN relations r2 ON r1.object = r2.subject
            WHERE r1.subject != r2.object 
              AND r1.relation != 'inferred_transitive'
              AND r2.relation != 'inferred_transitive'
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error:
            logger.exception("Erro na inferência SQL")
            return 0

    def query_subgraph(
        self,
        entity_names: List[str],
        limit: int = 30,
        allowed_relations: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Recupera a vizinhança de 2-HOPS (Deep RAG) usando auto-joins.
        Permite encontrar conexões ocultas que uma busca simples ignoraria.
        """
        if not entity_names:
            return []

        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Placeholders para as entidades semente
                placeholders = ", ".join(["?"] * len(entity_names))
                
                # Query de 2-Hops: Busca vizinhos diretos e vizinhos dos vizinhos
                query = f"""
                    SELECT DISTINCT subject, relation, object, source_doc, page_number
                    FROM relations
                    WHERE subject IN ({placeholders}) OR object IN ({placeholders})
                    UNION
                    SELECT DISTINCT r2.subject, r2.relation, r2.object, r2.source_doc, r2.page_number
                    FROM relations r1
                    JOIN relations r2 ON (r1.object = r2.subject OR r1.subject = r2.object)
                    WHERE r1.subject IN ({placeholders}) OR r1.object IN ({placeholders})
                """
                
                if allowed_relations:
                    rel_placeholders = ", ".join(["?"] * len(allowed_relations))
                    query = f"SELECT * FROM ({query}) WHERE relation IN ({rel_placeholders})"
                    # 4 sets of entity_names for the 4 IN clauses in the UNION query
                    params = entity_names + entity_names + entity_names + entity_names + allowed_relations
                else:
                    # 4 sets of entity_names for the 4 IN clauses in the UNION query
                    params = entity_names + entity_names + entity_names + entity_names

                query += " LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            logger.exception("Erro ao consultar subgrafo profundo")
            return []

    def count_entities(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

    def entity_degree(self, entity_name: str) -> Dict[str, int]:
        """Retorna grau de entrada, saída e total de uma entidade."""
        with self._connect() as conn:
            cursor = conn.cursor()
            name = self._resolve_canonical_name(cursor, entity_name)

            out_count = cursor.execute(
                "SELECT COUNT(*) FROM relations WHERE subject = ?", (name,)
            ).fetchone()[0]

            in_count = cursor.execute(
                "SELECT COUNT(*) FROM relations WHERE object = ?", (name,)
            ).fetchone()[0]

            return {"in": in_count, "out": out_count, "total": in_count + out_count}

    def top_hubs(self, limit: int = 10) -> List[Dict[str, int]]:
        """Retorna entidades mais conectadas (grau por in+out)."""
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT subject AS entity, COUNT(*) AS out_deg FROM relations GROUP BY subject"
            )
            out_rows = {r[0]: r[1] for r in cursor.fetchall()}

            cursor.execute(
                "SELECT object AS entity, COUNT(*) AS in_deg FROM relations GROUP BY object"
            )
            in_rows = {r[0]: r[1] for r in cursor.fetchall()}

            all_entities = set(out_rows.keys()) | set(in_rows.keys())
            degrees = []
            for e in all_entities:
                degrees.append(
                    {
                        "entity": e,
                        "in": in_rows.get(e, 0),
                        "out": out_rows.get(e, 0),
                        "total": in_rows.get(e, 0) + out_rows.get(e, 0),
                    }
                )

            degrees.sort(key=lambda x: x["total"], reverse=True)
            return degrees[:limit]

    def trending_entities(self, days: int = 30, limit: int = 20) -> List[Dict[str, int]]:
        """Retorna entidades com maior ocorrência em relações recentes."""
        since = datetime.now() - timedelta(days=days)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT subject AS entity FROM relations WHERE timestamp >= ? UNION ALL SELECT object AS entity FROM relations WHERE timestamp >= ?",
                (since_str, since_str),
            )
            rows = cursor.fetchall()

            counter: Dict[str, int] = {}
            for row in rows:
                entity = row["entity"]
                counter[entity] = counter.get(entity, 0) + 1

            sorted_trend = sorted(counter.items(), key=lambda x: x[1], reverse=True)
            return [{"entity": e, "count": c} for e, c in sorted_trend[:limit]]
