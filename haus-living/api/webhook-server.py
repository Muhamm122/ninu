"""
Haus Living — FastAPI Webhook Listener
Receives order, payment (Midtrans/Xendit), and Instagram webhook events.
Persists all incoming payloads as timestamped JSON files.
"""

import hashlib
import hmac
import json
import os
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY", "MIDTRANS_SERVER_KEY")
WEBHOOK_DIR = Path(os.getenv("HAUS_WEBHOOK_DIR", os.path.expanduser("~/.hermes/haus-living/webhooks")))
WEBHOOK_DIR.mkdir(parents=True, exist_ok=True)

APP_VERSION = "1.0.0"
APP_NAME = "Haus Living Webhook Listener"

# ---------------------------------------------------------------------------
# Task Tracker DB
# ---------------------------------------------------------------------------

TASK_DB_PATH = Path(os.getenv("HAUS_TASK_DB", os.path.expanduser("~/.hermes/haus-living/tasks.db")))
TASK_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _get_task_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(TASK_DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            status TEXT DEFAULT 'done',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category)
    """)
    db.commit()
    return db

def _validate_api_key(x_api_key: Optional[str]) -> bool:
    expected = os.getenv("HAUS_TASK_API_KEY", "haus_living_task_key_2026")
    if not x_api_key:
        return False
    return hmac.compare_digest(x_api_key.strip(), expected)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("haus-living.webhooks")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Webhook listener for Haus Living — orders, payments, Instagram.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _persist_webhook(category: str, payload: Dict[str, Any]) -> Path:
    """Save webhook payload to a timestamped JSON file."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Include microseconds to avoid collisions under rapid fire
    us = datetime.now(timezone.utc).strftime("%f")
    filename = f"{category}_{ts}_{us}.json"
    filepath = WEBHOOK_DIR / filename
    record = {
        "received_at": _now_iso(),
        "category": category,
        "payload": payload,
    }
    filepath.write_text(json.dumps(record, indent=2, default=str))
    logger.info("Persisted webhook %s → %s", category, filepath)
    return filepath


def _verify_midtrans_signature(payload: Dict[str, Any], signature_key: Optional[str]) -> bool:
    """
    Verify Midtrans signature.
    Midtrans sends a `signature_key` in the payload which is
    SHA512(order_id + status_code + gross_amount + server_key).
    """
    if not signature_key:
        return False

    order_id = str(payload.get("order_id", ""))
    status_code = str(payload.get("status_code", ""))
    gross_amount = str(payload.get("gross_amount", ""))

    expected = hashlib.sha512(
        (order_id + status_code + gross_amount + MIDTRANS_SERVER_KEY).encode()
    ).hexdigest()

    return hmac.compare_digest(expected, signature_key)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", summary="API info")
async def api_info():
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "brand": "Haus Living",
        "endpoints": {
            "order_webhook": "POST /webhook/order",
            "payment_webhook": "POST /webhook/payment",
            "instagram_webhook": "POST /webhook/ig",
            "health_check": "GET /webhook/health",
            "task_stats": "GET /task/stats",
            "task_list": "GET /task/list",
            "task_add": "POST /task/add",
            "task_update": "PUT /task/{id}",
            "task_delete": "DELETE /task/{id}",
        },
        "webhook_storage": str(WEBHOOK_DIR),
    }


@app.get("/webhook/health", summary="Health check")
async def health_check():
    webhook_count = len(list(WEBHOOK_DIR.glob("*.json")))
    return {
        "status": "healthy",
        "timestamp": _now_iso(),
        "webhook_dir": str(WEBHOOK_DIR),
        "stored_webhooks": webhook_count,
    }


@app.post("/webhook/order", summary="Receive new order notifications")
async def webhook_order(request: Request):
    """
    Receives new order notifications.
    Expected: JSON body with order details.
    """
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error("Failed to parse order webhook body: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")

    filepath = _persist_webhook("order", payload)
    logger.info("Order webhook received: order_id=%s", payload.get("order_id", "N/A"))

    return JSONResponse(
        status_code=200,
        content={
            "status": "received",
            "category": "order",
            "stored_as": filepath.name,
            "timestamp": _now_iso(),
        },
    )


@app.post("/webhook/payment", summary="Payment status updates (Midtrans / Xendit)")
async def webhook_payment(request: Request):
    """
    Receives payment status updates from Midtrans or Xendit.
    Midtrans: signature_key verified via SHA512.
    Xendit: verification via X-Callback-Token header (placeholder).
    """
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error("Failed to parse payment webhook body: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")

    # Detect payment provider
    provider = payload.get("payment_type") or "unknown"
    is_midtrans = "signature_key" in payload or "order_id" in payload
    signature_verified = False

    if is_midtrans:
        sig_key = payload.get("signature_key")
        signature_verified = _verify_midtrans_signature(payload, sig_key)
        provider = "midtrans"
        if not signature_verified:
            logger.warning("Midtrans signature verification FAILED for order_id=%s", payload.get("order_id"))
        else:
            logger.info("Midtrans signature verified for order_id=%s", payload.get("order_id"))
    else:
        # Xendit uses X-Callback-Token header for verification
        callback_token = request.headers.get("x-callback-token", "")
        xendit_token = os.getenv("XENDIT_CALLBACK_TOKEN", "")
        if xendit_token and callback_token:
            signature_verified = hmac.compare_digest(callback_token, xendit_token)
            provider = "xendit"
        else:
            provider = "xendit" if "xendit" in str(payload).lower() else provider
            logger.info("Xendit callback token not configured — skipping verification")

    # Persist with verification metadata
    record_payload = {
        **payload,
        "_meta": {
            "provider": provider,
            "signature_verified": signature_verified,
        },
    }
    filepath = _persist_webhook("payment", record_payload)

    return JSONResponse(
        status_code=200,
        content={
            "status": "received",
            "category": "payment",
            "provider": provider,
            "signature_verified": signature_verified,
            "stored_as": filepath.name,
            "timestamp": _now_iso(),
        },
    )


@app.post("/webhook/ig", summary="Instagram webhook events")
async def webhook_instagram(request: Request):
    """
    Receives Instagram webhook events.
    Handles both:
      - GET verification challenge (hub.mode=subscribe) — via query params
      - POST event notifications (comments, mentions, story_replies, etc.)
    """
    # Instagram subscription verification (sent as POST with hub.* fields)
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error("Failed to parse Instagram webhook body: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Handle subscription verification challenge
    if payload.get("hub.mode") == "subscribe":
        challenge = payload.get("hub.challenge", "")
        verify_token = payload.get("hub.verify_token", "")
        expected_token = os.getenv("IG_VERIFY_TOKEN", "haus_living_verify")
        if verify_token != expected_token:
            raise HTTPException(status_code=403, detail="Verify token mismatch")
        logger.info("Instagram webhook subscription verified")
        return JSONResponse(status_code=200, content={"challenge": challenge})

    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")

    # X-Hub-Signature-256 header verification
    hub_sig = request.headers.get("x-hub-signature-256", "")
    ig_app_secret = os.getenv("IG_APP_SECRET", "")
    sig_verified = False
    if ig_app_secret and hub_sig:
        body_bytes = await request.body()
        expected_sig = "sha256=" + hmac.new(
            ig_app_secret.encode(), body_bytes, hashlib.sha256
        ).hexdigest()
        sig_verified = hmac.compare_digest(hub_sig, expected_sig)
        if not sig_verified:
            logger.warning("Instagram X-Hub-Signature-256 verification FAILED")

    record_payload = {
        **payload,
        "_meta": {
            "provider": "instagram",
            "signature_verified": sig_verified,
        },
    }
    filepath = _persist_webhook("ig", record_payload)

    return JSONResponse(
        status_code=200,
        content={
            "status": "received",
            "category": "instagram",
            "signature_verified": sig_verified,
            "stored_as": filepath.name,
            "timestamp": _now_iso(),
        },
    )


# ---------------------------------------------------------------------------
# Task Tracker Routes
# ---------------------------------------------------------------------------

@app.get("/task/stats", summary="Task tracker stats")
async def task_stats(x_api_key: Optional[str] = Header(None)):
    if not _validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    db = _get_task_db()
    try:
        total = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        done = db.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0]
        pending = db.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'").fetchone()[0]
        cats = db.execute("SELECT category, COUNT(*) as cnt FROM tasks GROUP BY category ORDER BY cnt DESC").fetchall()
        return {
            "total": total,
            "done": done,
            "pending": pending,
            "by_category": {r["category"]: r["cnt"] for r in cats},
        }
    finally:
        db.close()


@app.get("/task/list", summary="List tasks")
async def task_list(
    x_api_key: Optional[str] = Header(None),
    status: Optional[str] = Query(None, description="Filter by status: done, pending, all"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    if not _validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    db = _get_task_db()
    try:
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list = []
        if status and status != "all":
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = db.execute(query, params).fetchall()
        return {
            "tasks": [dict(r) for r in rows],
            "count": len(rows),
            "limit": limit,
            "offset": offset,
        }
    finally:
        db.close()


@app.post("/task/add", summary="Add a completed task")
async def task_add(request: Request, x_api_key: Optional[str] = Header(None)):
    if not _validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    category = (body.get("category") or "general").strip()
    status_val = (body.get("status") or "done").strip()
    if status_val not in ("done", "pending", "cancelled"):
        status_val = "done"
    note = (body.get("note") or "").strip()
    now = _now_iso()

    db = _get_task_db()
    try:
        cur = db.execute(
            "INSERT INTO tasks (title, category, status, note, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (title, category, status_val, note, now, now),
        )
        db.commit()
        return {
            "id": cur.lastrowid,
            "title": title,
            "category": category,
            "status": status_val,
            "created_at": now,
        }
    finally:
        db.close()


@app.put("/task/{task_id}", summary="Update a task")
async def task_update(task_id: int, request: Request, x_api_key: Optional[str] = Header(None)):
    if not _validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    db = _get_task_db()
    try:
        row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")

        title = (body.get("title") or row["title"]).strip()
        category = (body.get("category") or row["category"]).strip()
        status_val = (body.get("status") or row["status"]).strip()
        if status_val not in ("done", "pending", "cancelled"):
            status_val = row["status"]
        note = body.get("note", row["note"])
        now = _now_iso()

        db.execute(
            "UPDATE tasks SET title=?, category=?, status=?, note=?, updated_at=? WHERE id=?",
            (title, category, status_val, note, now, task_id),
        )
        db.commit()
        return {"id": task_id, "title": title, "category": category, "status": status_val, "updated_at": now}
    finally:
        db.close()


@app.delete("/task/{task_id}", summary="Delete a task")
async def task_delete(task_id: int, x_api_key: Optional[str] = Header(None)):
    if not _validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    db = _get_task_db()
    try:
        row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        db.commit()
        return {"deleted": True, "id": task_id}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Generic exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
