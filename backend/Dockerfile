FROM python:3.12-slim AS base

WORKDIR /app

ARG ORACLE_INSTANTCLIENT_VERSION=19.31.0.0.0dbru
ARG ORACLE_INSTANTCLIENT_DIR=instantclient_19_31

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates unzip unixodbc libnsl2; \
    if apt-cache show libaio1 >/dev/null 2>&1; then \
        apt-get install -y --no-install-recommends libaio1; \
    else \
        apt-get install -y --no-install-recommends libaio1t64; \
        aio_lib_dir="$(dirname "$(find /usr/lib -name 'libaio.so.1t64' -print -quit)")"; \
        ln -sf "${aio_lib_dir}/libaio.so.1t64" "${aio_lib_dir}/libaio.so.1"; \
    fi; \
    oracle_instantclient_url="https://download.oracle.com/otn_software/linux/instantclient/1931000/instantclient-basiclite-linux.x64-${ORACLE_INSTANTCLIENT_VERSION}.zip"; \
    curl -fsSL "${oracle_instantclient_url}" -o /tmp/instantclient.zip; \
    mkdir -p /opt/oracle; \
    unzip -q /tmp/instantclient.zip -d /opt/oracle; \
    echo "/opt/oracle/${ORACLE_INSTANTCLIENT_DIR}" > /etc/ld.so.conf.d/oracle-instantclient.conf; \
    ldconfig; \
    rm -f /tmp/instantclient.zip; \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev,all-drivers]"

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=3s --retries=12 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
