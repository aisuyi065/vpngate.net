FROM node:22-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update \
  && apt-get install -y --no-install-recommends openvpn iproute2 iputils-ping curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*
COPY backend ./backend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN python -m venv /app/.venv \
  && /app/.venv/bin/pip install --upgrade pip \
  && /app/.venv/bin/pip install -e ./backend
ENV VPNGATE_BIND_HOST=0.0.0.0
ENV VPNGATE_BIND_PORT=8000
ENV VPNGATE_DATA_DIR=/app/data
EXPOSE 8000
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "app.main:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8000"]
