# Haus Living Webhook Listener - Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard]

# Copy application code
COPY webhook-server.py .

# Create webhook storage directory
RUN mkdir -p /root/.hermes/haus-living/webhooks

# Environment defaults
ENV MIDTRANS_SERVER_KEY=MIDTRANS_SERVER_KEY
ENV XENDIT_CALLBACK_TOKEN=***
ENV IG_VERIFY_TOKEN=haus_living_verify
ENV IG_APP_SECRET=***
ENV HAUS_WEBHOOK_DIR=/root/.hermes/haus-living/webhooks
ENV PORT=8000

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/webhook/health')" || exit 1

CMD ["python", "-m", "uvicorn", "webhook-server:app", "--host", "0.0.0.0", "--port", "8000"]
