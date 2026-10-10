"""SQLite persistence (stdlib only)."""
from __future__ import annotations

import gzip
import json
import sqlite3
import threading
import time
from pathlib import Path

from ..config import DEFAULT_SETTINGS, merge_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at REAL NOT NULL,
    settings TEXT NOT NULL,
    calibration TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    modality TEXT NOT NULL,
    n INTEGER NOT NULL,
    day TEXT NOT NULL,
    started_at REAL NOT NULL,
    finished_at REAL,
    config TEXT NOT NULL,
    plan TEXT NOT NULL,
    accuracy REAL,
    mean_score REAL,
    next_n INTEGER,
    status TEXT NOT NULL DEFAULT 'running'
);
CREATE INDEX IF NOT EXISTS blocks_profile ON blocks(profile_id, modality, started_at);
CREATE TABLE IF NOT EXISTS trials (
    block_id INTEGER NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    targets TEXT NOT NULL,
    score REAL,
    correct INTEGER,
    valid INTEGER,
    confused_with TEXT,
    result TEXT,
    response BLOB,
    created_at REAL NOT NULL,
    PRIMARY KEY (block_id, idx)
);
CREATE TABLE IF NOT EXISTS item_stats (
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    modality TEXT NOT NULL,
    item_id TEXT NOT NULL,
    stats TEXT NOT NULL,
    PRIMARY KEY (profile_id, modality, item_id)
);
CREATE TABLE IF NOT EXISTS exclusions (
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    modality TEXT NOT NULL,
    item_id TEXT NOT NULL,
    PRIMARY KEY (profile_id, modality, item_id)
);
"""

KEEP_RESPONSES_BLOCKS = 30  # raw responses kept for replay in the most recent blocks only


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- helpers -----------------------------------------------------------------------
    def _q(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(sql, args).fetchall()

    def _x(self, sql: str, args: tuple = ()) -> int:
        with self._lock:
            cur = self.conn.execute(sql, args)
            self.conn.commit()
            return cur.lastrowid

    # -- profiles ----------------------------------------------------------------------
    def _profile(self, row: sqlite3.Row) -> dict:
        return {"id": row["id"], "name": row["name"], "created_at": row["created_at"],
                "settings": merge_settings(DEFAULT_SETTINGS, json.loads(row["settings"])),
                "calibration": json.loads(row["calibration"])}

    def create_profile(self, name: str, settings: dict | None = None) -> dict:
        pid = self._x("INSERT INTO profiles(name, created_at, settings) VALUES (?,?,?)",
                      (name, time.time(), json.dumps(settings or {})))
        return self.get_profile(pid)

    def list_profiles(self) -> list[dict]:
        return [self._profile(r) for r in self._q("SELECT * FROM profiles ORDER BY id")]

    def get_profile(self, pid: int) -> dict | None:
        rows = self._q("SELECT * FROM profiles WHERE id=?", (pid,))
        return self._profile(rows[0]) if rows else None

    def update_profile(self, pid: int, name: str | None = None, settings: dict | None = None) -> dict:
        prof = self.get_profile(pid)
        if prof is None:
            raise KeyError(pid)
        stored = json.loads(self._q("SELECT settings FROM profiles WHERE id=?", (pid,))[0]["settings"])
        if settings:
            stored = merge_settings(stored, settings)
        self._x("UPDATE profiles SET name=?, settings=? WHERE id=?", (name or prof["name"], json.dumps(stored), pid))
        return self.get_profile(pid)

    def set_calibration(self, pid: int, key: str, value: dict) -> dict:
        prof = self.get_profile(pid)
        if prof is None:
            raise KeyError(pid)
        cal = prof["calibration"]
        cal[key] = value
        self._x("UPDATE profiles SET calibration=? WHERE id=?", (json.dumps(cal), pid))
        return self.get_profile(pid)

    def delete_profile(self, pid: int) -> None:
        self._x("DELETE FROM profiles WHERE id=?", (pid,))

    # -- blocks & trials ---------------------------------------------------------------
    def create_block(self, pid: int, modality: str, n: int, config: dict, plan: list[dict], day: str) -> int:
        return self._x("INSERT INTO blocks(profile_id, modality, n, day, started_at, config, plan) VALUES (?,?,?,?,?,?,?)",
                       (pid, modality, n, day, time.time(), json.dumps(config), json.dumps(plan)))

    def get_block(self, bid: int) -> dict | None:
        rows = self._q("SELECT * FROM blocks WHERE id=?", (bid,))
        if not rows:
            return None
        r = dict(rows[0])
        r["config"] = json.loads(r["config"])
        r["plan"] = json.loads(r["plan"])
        return r

    def finish_block(self, bid: int, accuracy: float | None, mean_score: float | None, next_n: int) -> None:
        self._x("UPDATE blocks SET finished_at=?, accuracy=?, mean_score=?, next_n=?, status='finished' WHERE id=?",
                (time.time(), accuracy, mean_score, next_n, bid))
        self._prune_responses()

    def list_blocks(self, pid: int, modality: str | None = None, limit: int = 1000) -> list[dict]:
        if modality:
            rows = self._q("SELECT * FROM blocks WHERE profile_id=? AND modality=? ORDER BY started_at DESC LIMIT ?",
                           (pid, modality, limit))
        else:
            rows = self._q("SELECT * FROM blocks WHERE profile_id=? ORDER BY started_at DESC LIMIT ?", (pid, limit))
        out = []
        for r in rows:
            d = dict(r)
            d.pop("plan")
            d["config"] = json.loads(d["config"])
            out.append(d)
        return out

    def save_trial(self, bid: int, idx: int, item_id: str, targets: list, score: float | None, correct: bool | None,
                   valid: bool, confused_with: str | None, result: dict, response: dict | None) -> None:
        blob = gzip.compress(json.dumps(response).encode()) if response is not None else None
        self._x("INSERT OR REPLACE INTO trials(block_id, idx, item_id, targets, score, correct, valid, confused_with, "
                "result, response, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (bid, idx, item_id, json.dumps(targets), score, None if correct is None else int(correct), int(valid),
                 confused_with, json.dumps(result), blob, time.time()))

    def list_trials(self, bid: int, with_responses: bool = False) -> list[dict]:
        out = []
        for r in self._q("SELECT * FROM trials WHERE block_id=? ORDER BY idx", (bid,)):
            d = dict(r)
            d["targets"] = json.loads(d["targets"])
            d["result"] = json.loads(d["result"]) if d["result"] else None
            blob = d.pop("response")
            if with_responses and blob:
                d["response"] = json.loads(gzip.decompress(blob))
            out.append(d)
        return out

    def trials_for_profile(self, pid: int, modality: str) -> list[dict]:
        rows = self._q("SELECT t.item_id, t.targets, t.score, t.correct, t.valid, b.day FROM trials t "
                       "JOIN blocks b ON b.id=t.block_id WHERE b.profile_id=? AND b.modality=?", (pid, modality))
        return [dict(r) for r in rows]

    def _prune_responses(self) -> None:
        self._x("UPDATE trials SET response=NULL WHERE block_id NOT IN "
                "(SELECT id FROM blocks ORDER BY started_at DESC LIMIT ?)", (KEEP_RESPONSES_BLOCKS,))

    # -- item stats & exclusions ---------------------------------------------------------
    def get_stats(self, pid: int, modality: str) -> dict[str, dict]:
        return {r["item_id"]: json.loads(r["stats"]) for r in
                self._q("SELECT item_id, stats FROM item_stats WHERE profile_id=? AND modality=?", (pid, modality))}

    def put_stats(self, pid: int, modality: str, item_id: str, stats: dict) -> None:
        self._x("INSERT OR REPLACE INTO item_stats(profile_id, modality, item_id, stats) VALUES (?,?,?,?)",
                (pid, modality, item_id, json.dumps(stats)))

    def exclusions(self, pid: int, modality: str) -> set[str]:
        return {r["item_id"] for r in
                self._q("SELECT item_id FROM exclusions WHERE profile_id=? AND modality=?", (pid, modality))}

    def set_excluded(self, pid: int, modality: str, item_id: str, excluded: bool) -> None:
        if excluded:
            self._x("INSERT OR IGNORE INTO exclusions(profile_id, modality, item_id) VALUES (?,?,?)", (pid, modality, item_id))
        else:
            self._x("DELETE FROM exclusions WHERE profile_id=? AND modality=? AND item_id=?", (pid, modality, item_id))
