"""
FiBu Mate Datenbank-Zugriffsschicht
===================================

Zweck:
- Zentrale SQLite-Datenbank fuer den Start verwenden.
- Struktur so kapseln, dass spaeter ein SQL-Server-Backend ergaenzt werden kann.
- Direkte sqlite3-Aufrufe im Hauptprogramm vermeiden.

Einfügepfad:
G:\BUC\FM Anwendung\Fibu_Mate_Doc\Database\fibu_mate_db.py

Hinweis:
Diese Datei ist bewusst eigenständig und nutzt nur Python-Standardbibliotheken.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_BASE_DIR = Path(r"G:\BUC\FM Anwendung")
DEFAULT_DOC_DIR = DEFAULT_BASE_DIR / "Fibu_Mate_Doc"
DEFAULT_CONFIG_PATH = DEFAULT_DOC_DIR / "Config" / "database_config.json"


class FibuMateDbError(RuntimeError):
    """Basisklasse fuer Datenbankfehler in FiBu Mate."""


class FibuMateDbLockedError(FibuMateDbError):
    """Wird ausgelöst, wenn SQLite nach mehreren Versuchen noch gesperrt ist."""


class FibuMateDb:
    """Datenbank-Fassade fuer FiBu Mate.

    Aktuell produktiv implementiert:
    - SQLite

    Vorbereitet fuer spaeter:
    - SQL Server ueber separate Implementierung/Adapter
    """

    def __init__(self, config_path: Optional[str | Path] = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        self.database_mode = str(self.config.get("database_mode", "sqlite")).lower()
        if self.database_mode != "sqlite":
            raise FibuMateDbError(
                f"Datenbankmodus '{self.database_mode}' ist in dieser Version noch nicht aktiv implementiert. "
                "Bitte database_mode='sqlite' verwenden."
            )
        sqlite_cfg = self.config.get("sqlite", {})
        self.db_path = Path(sqlite_cfg.get("database_path", DEFAULT_DOC_DIR / "Database" / "fibu_mate.db"))
        self.timeout_seconds = int(sqlite_cfg.get("timeout_seconds", 30))
        self.retry_attempts = int(sqlite_cfg.get("busy_retry_attempts", 5))
        self.retry_wait_ms = int(sqlite_cfg.get("busy_retry_wait_ms", 500))
        self.journal_mode = str(sqlite_cfg.get("journal_mode", "WAL")).upper()
        self.use_foreign_keys = bool(sqlite_cfg.get("foreign_keys", True))

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Datenbank-Konfiguration nicht gefunden: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def connect(self) -> sqlite3.Connection:
        """Oeffnet eine SQLite-Verbindung mit produktionsnahen Defaults."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(self.db_path), timeout=self.timeout_seconds)
        con.row_factory = sqlite3.Row
        if self.use_foreign_keys:
            con.execute("PRAGMA foreign_keys = ON;")
        if self.journal_mode == "WAL":
            con.execute("PRAGMA journal_mode = WAL;")
        return con

    @contextmanager
    def connection(self):
        con = self.connect()
        try:
            yield con
        finally:
            con.close()

    @contextmanager
    def transaction(self):
        """Transaktion mit automatischem Commit/Rollback."""
        con = self.connect()
        try:
            con.execute("BEGIN;")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _execute_with_retry(self, fn):
        last_exc = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                return fn()
            except sqlite3.OperationalError as exc:
                last_exc = exc
                msg = str(exc).lower()
                if "locked" not in msg and "busy" not in msg:
                    raise
                time.sleep(self.retry_wait_ms / 1000)
        raise FibuMateDbLockedError(
            f"SQLite-Datenbank ist nach {self.retry_attempts} Versuchen noch gesperrt: {last_exc}"
        )

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> int:
        """Fuehrt INSERT/UPDATE/DELETE aus und gibt lastrowid zurueck."""
        def run():
            with self.transaction() as con:
                cur = con.execute(sql, params)
                return int(cur.lastrowid or 0)
        return self._execute_with_retry(run)

    def executemany(self, sql: str, seq_of_params: Iterable[Tuple[Any, ...]]) -> None:
        def run():
            with self.transaction() as con:
                con.executemany(sql, seq_of_params)
        self._execute_with_retry(run)

    def fetch_all(self, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        with self.connection() as con:
            rows = con.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def fetch_one(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
        with self.connection() as con:
            row = con.execute(sql, params).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # App Settings
    # ------------------------------------------------------------------
    def get_setting(self, key: str, default: str = "") -> str:
        row = self.fetch_one("SELECT setting_value FROM app_settings WHERE setting_key = ?", (key,))
        return str(row["setting_value"]) if row else default

    def set_setting(self, key: str, value: str, username: str = "") -> None:
        self.execute(
            """
            INSERT INTO app_settings(setting_key, setting_value, updated_at, updated_by)
            VALUES (?, ?, datetime('now'), ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = datetime('now'),
                updated_by = excluded.updated_by
            """,
            (key, value, username),
        )

    # ------------------------------------------------------------------
    # Benutzer / Rollen / Berechtigungen
    # ------------------------------------------------------------------
    def ensure_user(self, username: str, display_name: Optional[str] = None, email: str = "") -> int:
        username = (username or "").strip()
        if not username:
            raise ValueError("username darf nicht leer sein")
        display_name = display_name or username
        existing = self.fetch_one("SELECT id FROM users WHERE username = ?", (username,))
        if existing:
            return int(existing["id"])
        return self.execute(
            "INSERT INTO users(username, display_name, email, active, created_at, updated_at) VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))",
            (username, display_name, email),
        )

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        return self.fetch_one("SELECT * FROM users WHERE username = ?", (username,))

    def list_users(self, active_only: bool = False) -> List[Dict[str, Any]]:
        if active_only:
            return self.fetch_all("SELECT * FROM users WHERE active = 1 ORDER BY display_name")
        return self.fetch_all("SELECT * FROM users ORDER BY display_name")

    def set_last_login(self, username: str) -> None:
        self.execute("UPDATE users SET last_login_at = datetime('now') WHERE username = ?", (username,))

    def list_permissions_for_user(self, username: str) -> List[str]:
        rows = self.fetch_all(
            """
            SELECT DISTINCT p.permission_key
            FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN role_permissions rp ON rp.role_id = ur.role_id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE u.username = ? AND u.active = 1
            ORDER BY p.permission_key
            """,
            (username,),
        )
        return [str(r["permission_key"]) for r in rows]

    def user_has_permission(self, username: str, permission_key: str) -> bool:
        user = self.get_user(username)
        if not user or not int(user.get("active", 0)):
            return False
        if int(user.get("is_admin", 0)):
            return True
        return permission_key in self.list_permissions_for_user(username)

    # ------------------------------------------------------------------
    # Modul-Daten generisch als JSON
    # ------------------------------------------------------------------
    def save_module_record(
        self,
        module_key: str,
        record_type: str,
        payload: Dict[str, Any],
        record_key: str = "",
        username: str = "",
        record_id: Optional[int] = None,
    ) -> int:
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if record_id:
            self.execute(
                """
                UPDATE module_data
                SET module_key = ?, record_type = ?, record_key = ?, payload_json = ?,
                    updated_at = datetime('now'), updated_by = ?, row_version = row_version + 1
                WHERE id = ?
                """,
                (module_key, record_type, record_key, payload_json, username, record_id),
            )
            return int(record_id)
        return self.execute(
            """
            INSERT INTO module_data(module_key, record_type, record_key, payload_json, created_by, updated_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (module_key, record_type, record_key, payload_json, username, username),
        )

    def get_module_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        row = self.fetch_one("SELECT * FROM module_data WHERE id = ?", (record_id,))
        if not row:
            return None
        row["payload"] = json.loads(row.get("payload_json") or "{}")
        return row

    def list_module_records(self, module_key: str, record_type: str) -> List[Dict[str, Any]]:
        rows = self.fetch_all(
            "SELECT * FROM module_data WHERE module_key = ? AND record_type = ? ORDER BY updated_at DESC, id DESC",
            (module_key, record_type),
        )
        for row in rows:
            row["payload"] = json.loads(row.get("payload_json") or "{}")
        return rows

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------
    def log_audit(
        self,
        action_key: str,
        username: str = "",
        module_key: str = "",
        entity_type: str = "",
        entity_id: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        return self.execute(
            """
            INSERT INTO audit_log(username, module_key, action_key, entity_type, entity_id, details_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, module_key, action_key, entity_type, entity_id, json.dumps(details or {}, ensure_ascii=False)),
        )

    def log_update(
        self,
        status: str,
        username: str = "",
        old_version: str = "",
        new_version: str = "",
        update_type: str = "",
        message: str = "",
    ) -> int:
        return self.execute(
            """
            INSERT INTO update_log(username, machine_name, old_version, new_version, update_type, status, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (username, os.environ.get("COMPUTERNAME", ""), old_version, new_version, update_type, status, message),
        )

    # ------------------------------------------------------------------
    # AFI Exportprotokoll
    # ------------------------------------------------------------------
    def create_afi_export_run(
        self,
        username: str = "",
        source_invoice_path: str = "",
        assignment_path: str = "",
        export_path: str = "",
        booking_circle: str = "",
        cost_description: str = "",
        row_count: int = 0,
        export_total: str = "",
        status: str = "created",
        message: str = "",
    ) -> int:
        return self.execute(
            """
            INSERT INTO afi_export_runs(username, source_invoice_path, assignment_path, export_path,
                booking_circle, cost_description, row_count, export_total, status, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                source_invoice_path,
                assignment_path,
                export_path,
                booking_circle,
                cost_description,
                int(row_count or 0),
                export_total,
                status,
                message,
            ),
        )


_db_singleton: Optional[FibuMateDb] = None


def get_db(config_path: Optional[str | Path] = None) -> FibuMateDb:
    """Singleton-Zugriff fuer einfache Integration in bestehende Module."""
    global _db_singleton
    if _db_singleton is None or config_path is not None:
        _db_singleton = FibuMateDb(config_path=config_path)
    return _db_singleton


if __name__ == "__main__":
    db = get_db()
    print("FiBu Mate DB-Verbindung OK")
    print("DB:", db.db_path)
    print("Schema-Version:", db.get_setting("database_schema_version", "unbekannt"))
    current_user = os.environ.get("USERNAME", "")
    if current_user:
        user_id = db.ensure_user(current_user, current_user)
        db.set_last_login(current_user)
        print(f"Benutzer geprueft/angelegt: {current_user} (ID {user_id})")
