"""RuleDatabase — SQLite-backed rule storage and queries.

Uses stdlib sqlite3 only. NO sqlalchemy, NO sqlite-utils.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from aecos.compliance.rules import Rule

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_name TEXT NOT NULL,
    section TEXT NOT NULL,
    title TEXT NOT NULL,
    ifc_classes TEXT NOT NULL DEFAULT '[]',
    check_type TEXT NOT NULL,
    property_path TEXT NOT NULL,
    check_value TEXT,
    region TEXT NOT NULL DEFAULT '*',
    citation TEXT NOT NULL DEFAULT '',
    effective_date TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_rules_code ON rules(code_name);
CREATE INDEX IF NOT EXISTS idx_rules_region ON rules(region);
"""

_FTS_SQL = """\
CREATE VIRTUAL TABLE IF NOT EXISTS rules_fts USING fts5(
    title, citation, content=rules, content_rowid=id
);
"""

_FTS_TRIGGER_SQL = """\
CREATE TRIGGER IF NOT EXISTS rules_ai AFTER INSERT ON rules BEGIN
    INSERT INTO rules_fts(rowid, title, citation)
    VALUES (new.id, new.title, new.citation);
END;

CREATE TRIGGER IF NOT EXISTS rules_ad AFTER DELETE ON rules BEGIN
    INSERT INTO rules_fts(rules_fts, rowid, title, citation)
    VALUES ('delete', old.id, old.title, old.citation);
END;

CREATE TRIGGER IF NOT EXISTS rules_au AFTER UPDATE ON rules BEGIN
    INSERT INTO rules_fts(rules_fts, rowid, title, citation)
    VALUES ('delete', old.id, old.title, old.citation);
    INSERT INTO rules_fts(rowid, title, citation)
    VALUES (new.id, new.title, new.citation);
END;
"""


class RuleDatabase:
    """SQLite-backed rule database with full-text search.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Use ``':memory:'`` for
        in-memory databases (useful for testing).
    auto_seed:
        If *True* (default), seed the database with initial rules on
        first access if the rules table is empty.
    """

    def __init__(self, db_path: str | Path = ":memory:", *, auto_seed: bool = True) -> None:
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None
        self._auto_seed = auto_seed

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy-initialise and return the database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._init_schema()
            if self._auto_seed and self._is_empty():
                self._seed()
        return self._conn

    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        self.conn.executescript(_SCHEMA_SQL)
        try:
            self.conn.executescript(_FTS_SQL)
            self.conn.executescript(_FTS_TRIGGER_SQL)
        except sqlite3.OperationalError:
            # FTS5 may not be available on all builds
            logger.debug("FTS5 not available; full-text search disabled.")
        self.conn.commit()

    def _is_empty(self) -> bool:
        """Return True if the rules table has no rows."""
        cur = self.conn.execute("SELECT COUNT(*) FROM rules")
        return cur.fetchone()[0] == 0

    def _seed(self) -> None:
        """Seed with initial rule data."""
        from aecos.compliance.seed_data import SEED_RULES
        for rule in SEED_RULES:
            self.add_rule(rule)
        logger.info("Seeded %d compliance rules.", len(SEED_RULES))

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- CRUD ----------------------------------------------------------------

    def add_rule(self, rule: Rule) -> int:
        """Insert a rule and return its new id."""
        cur = self.conn.execute(
            """\
            INSERT INTO rules (code_name, section, title, ifc_classes,
                               check_type, property_path, check_value,
                               region, citation, effective_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule.code_name,
                rule.section,
                rule.title,
                json.dumps(rule.ifc_classes),
                rule.check_type,
                rule.property_path,
                json.dumps(rule.check_value),
                rule.region,
                rule.citation,
                rule.effective_date,
            ),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def update_rule(self, rule_id: int, updates: dict[str, Any]) -> None:
        """Update specific fields of a rule."""
        allowed = {
            "code_name", "section", "title", "ifc_classes", "check_type",
            "property_path", "check_value", "region", "citation", "effective_date",
        }
        sets: list[str] = []
        vals: list[Any] = []
        for key, val in updates.items():
            if key not in allowed:
                continue
            if key == "ifc_classes":
                val = json.dumps(val)
            elif key == "check_value":
                val = json.dumps(val)
            sets.append(f"{key} = ?")
            vals.append(val)

        if not sets:
            return

        vals.append(rule_id)
        self.conn.execute(
            f"UPDATE rules SET {', '.join(sets)} WHERE id = ?",
            vals,
        )
        self.conn.commit()

    def delete_rule(self, rule_id: int) -> bool:
        """Delete a rule by id. Returns True if a row was deleted."""
        cur = self.conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def get_rule(self, rule_id: int) -> Rule | None:
        """Fetch a single rule by id."""
        cur = self.conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_rule(row)

    # -- Queries -------------------------------------------------------------

    def get_rules(
        self,
        *,
        ifc_class: str | None = None,
        region: str | None = None,
        code_name: str | None = None,
    ) -> list[Rule]:
        """Query rules with optional filters.

        Parameters
        ----------
        ifc_class:
            Filter to rules that apply to this IFC class.
        region:
            Filter to rules for this region (also includes '*' universal rules).
        code_name:
            Filter to a specific code (e.g., 'IBC2024').
        """
        clauses: list[str] = []
        params: list[Any] = []

        if ifc_class:
            # Match rules where ifc_classes JSON array contains the class
            clauses.append("(ifc_classes LIKE ? OR ifc_classes = '[]' OR ifc_classes LIKE '%\"*\"%')")
            params.append(f'%"{ifc_class}"%')

        if region:
            clauses.append("(region = ? OR region = '*')")
            params.append(region)

        if code_name:
            clauses.append("code_name = ?")
            params.append(code_name)

        where = " AND ".join(clauses) if clauses else "1=1"
        cur = self.conn.execute(f"SELECT * FROM rules WHERE {where}", params)
        return [self._row_to_rule(row) for row in cur.fetchall()]

    def search_rules(self, query: str) -> list[Rule]:
        """Full-text search on rule title and citation.

        Falls back to LIKE search if FTS5 is unavailable.
        """
        try:
            cur = self.conn.execute(
                """\
                SELECT rules.* FROM rules_fts
                JOIN rules ON rules_fts.rowid = rules.id
                WHERE rules_fts MATCH ?
                """,
                (query,),
            )
            return [self._row_to_rule(row) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            # FTS not available — fallback to LIKE
            like = f"%{query}%"
            cur = self.conn.execute(
                "SELECT * FROM rules WHERE title LIKE ? OR citation LIKE ?",
                (like, like),
            )
            return [self._row_to_rule(row) for row in cur.fetchall()]

    def count(self) -> int:
        """Return total number of rules."""
        cur = self.conn.execute("SELECT COUNT(*) FROM rules")
        return cur.fetchone()[0]

    # -- Internal ------------------------------------------------------------

    @staticmethod
    def _row_to_rule(row: sqlite3.Row) -> Rule:
        """Convert a database row to a Rule model."""
        return Rule(
            id=row["id"],
            code_name=row["code_name"],
            section=row["section"],
            title=row["title"],
            ifc_classes=json.loads(row["ifc_classes"]),
            check_type=row["check_type"],
            property_path=row["property_path"],
            check_value=json.loads(row["check_value"]),
            region=row["region"],
            citation=row["citation"],
            effective_date=row["effective_date"],
        )
