FROM python:3.11-slim

WORKDIR /app

# Telegram signal delivery (Railway Variables override these defaults)
ENV TELEGRAM_ENABLED=true \
    TELEGRAM_BOT_TOKEN=8858234987:AAGpTkm4hvCcilH_pRQQDxLekIdqz6IbtrY \
    TELEGRAM_CHAT_ID=-5559692993

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates tar \
    && rm -rf /var/lib/apt/lists/*

# Install the current Kraken CLI release for Linux x86_64.
# The old kraken-exchange URL returned 404; the project now publishes
# binaries under krakenfx/kraken-cli.
RUN set -eux; \
    curl --proto '=https' --tlsv1.2 -fsSL \
      https://github.com/krakenfx/kraken-cli/releases/download/v0.4.1/kraken-cli-x86_64-unknown-linux-gnu.tar.gz \
      -o /tmp/kraken-cli.tar.gz; \
    mkdir -p /tmp/kraken-cli; \
    tar -xzf /tmp/kraken-cli.tar.gz -C /tmp/kraken-cli; \
    find /tmp/kraken-cli -type f -name kraken -exec install -m 0755 {} /usr/local/bin/kraken \\; ; \
    /usr/local/bin/kraken --version; \
    rm -rf /tmp/kraken-cli /tmp/kraken-cli.tar.gz

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs /app/validation

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python3 agent.py --status || exit 1

ENTRYPOINT ["python3"]
CMD ["agent.py"]
