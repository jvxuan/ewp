#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记事 APP 原型后端（零第三方依赖，标准库）
- SQLite 持久化（作为服务端“云端”存储，多浏览器/设备访问同一服务即同步）
- REST API + 静态文件托管
运行：python3 server.py  ，默认 http://127.0.0.1:8000
"""
import base64
import datetime
import html
import json
import os
import re
import sqlite3
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.path.join(DATA_DIR, "notes.db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

PORT = int(os.environ.get("PORT", "8000"))


# ----------------------------- 数据库 -----------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL DEFAULT '',
            content     TEXT NOT NULL DEFAULT '',
            category    TEXT NOT NULL DEFAULT '未分类',
            tags        TEXT NOT NULL DEFAULT '[]',
            todos       TEXT NOT NULL DEFAULT '[]',
            reminder_at TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def row_to_note(row):
    if row is None:
        return None
    try:
        tags = json.loads(row["tags"])
    except (json.JSONDecodeError, TypeError):
        tags = []
    try:
        todos = json.loads(row["todos"])
    except (json.JSONDecodeError, TypeError):
        todos = []
    return {
        "id": row["id"],
        "title": row["title"] or "",
        "content": row["content"] or "",
        "category": row["category"] or "未分类",
        "tags": tags,
        "todos": todos,
        "reminder_at": row["reminder_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ----------------------------- HTML 工具 -----------------------------

def html_to_text(content_html):
    """极简 HTML -> 纯文本（用于 txt/md 导出与摘要）。"""
    if not content_html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", content_html, flags=re.I)
    text = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", text, flags=re.I)
    text = re.sub(r"<li[^>]*>", "- ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def note_to_markdown(note):
    lines = [f"# {note['title'] or '无标题'}", ""]
    meta = []
    if note["category"]:
        meta.append(f"分类：{note['category']}")
    if note["tags"]:
        meta.append("标签：" + " ".join(f"#{t}" for t in note["tags"]))
    if note["reminder_at"]:
        meta.append(f"提醒：{note['reminder_at']}")
    if meta:
        lines += [" > ".join(meta), ""]
    if note["todos"]:
        lines.append("## 待办")
        for t in note["todos"]:
            box = "x" if t.get("done") else " "
            line = f"- [{box}] {t.get('text', '')}"
            if t.get("reminder"):
                line += f" （提醒 {t['reminder']}）"
            lines.append(line)
        lines.append("")
    body = html_to_text(note["content"])
    if body:
        lines += ["## 正文", "", body]
    return "\n".join(lines)


# ----------------------------- 请求处理 -----------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "NotesApp/1.0"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (now_iso(), fmt % args))

    # ---------- 基础响应 ----------
    def _send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_bytes(self, body, ctype, status=200, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    # ---------- 路由 ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/notes":
            return self.api_list_notes(qs)
        if path.startswith("/api/notes/"):
            parts = path.strip("/").split("/")
            # /api/notes/<id>
            if len(parts) == 3 and parts[2].isdigit():
                return self.api_get_note(int(parts[2]))
            # /api/notes/<id>/export
            if len(parts) == 4 and parts[2].isdigit() and parts[3] == "export":
                return self.api_export(int(parts[2]), qs)
        if path == "/api/meta":
            return self.api_meta()

        # 静态资源
        if path == "/" or path == "/index.html":
            return self.serve_static("index.html", "text/html; charset=utf-8")
        if path.startswith("/static/"):
            return self.serve_static(path[len("/static/"):], self._ctype(path))
        if path.startswith("/uploads/"):
            return self.serve_upload(path[len("/uploads/"):])
        self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/notes":
            return self.api_create_note()
        if parsed.path == "/api/images":
            return self.api_upload_image()
        self._send_json({"error": "not found"}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "notes" and parts[2].isdigit():
            return self.api_update_note(int(parts[2]))
        self._send_json({"error": "not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "notes" and parts[2].isdigit():
            return self.api_delete_note(int(parts[2]))
        self._send_json({"error": "not found"}, 404)

    # ---------- 笔记 API ----------
    def api_list_notes(self, qs):
        conn = get_db()
        sql = "SELECT * FROM notes WHERE 1=1"
        args = []
        q = (qs.get("q") or [""])[0].strip()
        category = (qs.get("category") or [""])[0].strip()
        tag = (qs.get("tag") or [""])[0].strip()
        if q:
            sql += " AND (title LIKE ? OR content LIKE ?)"
            args += [f"%{q}%", f"%{q}%"]
        if category:
            sql += " AND category = ?"
            args.append(category)
        if tag:
            sql += " AND tags LIKE ?"
            args.append(f'%"{tag}"%')
        sql += " ORDER BY updated_at DESC"
        rows = conn.execute(sql, args).fetchall()
        notes = [row_to_note(r) for r in rows]
        # 标签在 JSON 中模糊匹配可能误伤，二次精确过滤
        if tag:
            notes = [n for n in notes if tag in n["tags"]]
        conn.close()
        self._send_json({"notes": notes})

    def api_get_note(self, note_id):
        conn = get_db()
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        conn.close()
        if not row:
            return self._send_json({"error": "note not found"}, 404)
        self._send_json(row_to_note(row))

    def _validate(self, body):
        def clean_text(v):
            if not isinstance(v, str):
                return ""
            v = v.strip()
            return "" if v.lower() in ("undefined", "null") else v

        title = clean_text(body.get("title"))
        content = body.get("content")
        if not isinstance(content, str):
            content = ""
        category = clean_text(body.get("category")) or "未分类"
        tags = body.get("tags") or []
        if not isinstance(tags, list):
            tags = []
        tags = [clean_text(t) for t in tags]
        tags = [t for t in tags if t]
        todos = body.get("todos") or []
        if not isinstance(todos, list):
            todos = []
        reminder_at = body.get("reminder_at") or None
        return {
            "title": title,
            "content": content,
            "category": category,
            "tags": tags,
            "todos": todos,
            "reminder_at": reminder_at,
        }

    def api_create_note(self):
        body = self._read_body()
        data = self._validate(body)
        ts = now_iso()
        conn = get_db()
        cur = conn.execute(
            """INSERT INTO notes (title, content, category, tags, todos, reminder_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["title"], data["content"], data["category"],
                json.dumps(data["tags"], ensure_ascii=False),
                json.dumps(data["todos"], ensure_ascii=False),
                data["reminder_at"], ts, ts,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (cur.lastrowid,)).fetchone()
        note = row_to_note(row)
        conn.close()
        self._send_json(note, 201)

    def api_update_note(self, note_id):
        body = self._read_body()
        data = self._validate(body)
        conn = get_db()
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not row:
            conn.close()
            return self._send_json({"error": "note not found"}, 404)
        conn.execute(
            """UPDATE notes SET title=?, content=?, category=?, tags=?, todos=?, reminder_at=?, updated_at=?
               WHERE id=?""",
            (
                data["title"], data["content"], data["category"],
                json.dumps(data["tags"], ensure_ascii=False),
                json.dumps(data["todos"], ensure_ascii=False),
                data["reminder_at"], now_iso(), note_id,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        note = row_to_note(row)
        conn.close()
        self._send_json(note)

    def api_delete_note(self, note_id):
        conn = get_db()
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not row:
            conn.close()
            return self._send_json({"error": "note not found"}, 404)
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        conn.close()
        self._send_json({"ok": True})

    def api_meta(self):
        conn = get_db()
        cats = [r["category"] for r in conn.execute("SELECT DISTINCT category FROM notes").fetchall()]
        tag_set = set()
        for r in conn.execute("SELECT tags FROM notes").fetchall():
            try:
                for t in json.loads(r["tags"]):
                    tag_set.add(t)
            except (json.JSONDecodeError, TypeError):
                pass
        conn.close()
        self._send_json({"categories": sorted(cats), "tags": sorted(tag_set)})

    def api_export(self, note_id, qs):
        conn = get_db()
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        conn.close()
        if not row:
            return self._send_json({"error": "note not found"}, 404)
        note = row_to_note(row)
        fmt = (qs.get("format") or ["md"])[0]
        ext = "txt" if fmt == "txt" else "md"
        if fmt == "txt":
            body = html_to_text(note["content"]).encode("utf-8")
            ctype = "text/plain; charset=utf-8"
        else:
            body = note_to_markdown(note).encode("utf-8")
            ctype = "text/markdown; charset=utf-8"
        fname = f"{note['title'] or 'note'}.{ext}"
        # HTTP 头仅允许 latin-1，中文文件名走 RFC 5987 编码
        disposition = (
            f"attachment; filename=\"note-{note_id}.{ext}\"; "
            f"filename*=UTF-8''{quote(fname)}"
        )
        self._send_bytes(body, ctype, headers={"Content-Disposition": disposition})

    def api_upload_image(self):
        body = self._read_body()
        data_url = body.get("data_url") or ""
        m = re.match(r"data:image/(png|jpeg|jpg|gif|webp);base64,(.+)", data_url, re.S)
        if not m:
            return self._send_json({"error": "invalid image data url"}, 400)
        ext = "jpg" if m.group(1) == "jpeg" else m.group(1)
        raw = base64.b64decode(m.group(2))
        name = f"{uuid.uuid4().hex}.{ext}"
        with open(os.path.join(UPLOAD_DIR, name), "wb") as f:
            f.write(raw)
        self._send_json({"url": f"/uploads/{name}"})

    # ---------- 静态 ----------
    def _ctype(self, path):
        if path.endswith(".css"):
            return "text/css; charset=utf-8"
        if path.endswith(".js"):
            return "application/javascript; charset=utf-8"
        if path.endswith(".svg"):
            return "image/svg+xml"
        return "application/octet-stream"

    def _safe_join(self, base, rel):
        full = os.path.normpath(os.path.join(base, rel))
        if not full.startswith(os.path.normpath(base)):
            return None
        return full

    def serve_static(self, rel, ctype):
        full = self._safe_join(STATIC_DIR, rel)
        if not full or not os.path.isfile(full):
            return self._send_json({"error": "not found"}, 404)
        with open(full, "rb") as f:
            self._send_bytes(f.read(), ctype)

    def serve_upload(self, rel):
        full = self._safe_join(UPLOAD_DIR, rel)
        if not full or not os.path.isfile(full):
            return self._send_json({"error": "not found"}, 404)
        ctype = self._ctype(full)
        with open(full, "rb") as f:
            self._send_bytes(f.read(), ctype)


def main():
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"记事 APP 原型已启动: http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
