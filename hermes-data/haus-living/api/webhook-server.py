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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, HTTPException, Header
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
