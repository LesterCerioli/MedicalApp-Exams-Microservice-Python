FROM debian:bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libgdbm-dev \
    libdb5.3-dev \
    libbz2-dev \
    libexpat1-dev \
    liblzma-dev \
    tk-dev \
    libffi-dev \
    wget \
    curl \
    git \
    libpq-dev \
    cargo \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*


RUN wget --no-check-certificate https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz && \
    tar -xzf Python-3.12.0.tgz && \
    cd Python-3.12.0 && \
    ./configure --enable-optimizations --enable-shared && \
    make -j$(nproc) && \
    make altinstall && \
    cd .. && \
    rm -rf Python-3.12.0 Python-3.12.0.tgz


RUN ldconfig && \
    ln -sf /usr/local/bin/python3.12 /usr/local/bin/python3 && \
    ln -sf /usr/local/bin/python3.12 /usr/local/bin/python && \
    ln -sf /usr/local/bin/pip3.12 /usr/local/bin/pip3 && \
    ln -sf /usr/local/bin/pip3.12 /usr/local/bin/pip

# 📦 Atualiza pip e instala dependências
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pipdeptree maturin


RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod -R 755 /app && \
    chown -R appuser:appuser /app

ENV DB_HOST=aws-0-us-east-1.pooler.supabase.com \
    DB_PORT=6543 \
    DB_USER=postgres.qfaqmphfzdiwhtobdbku \
    DB_PASSWORD=ESPnJR9OkBBw7HE3 \
    DB_NAME=medical_db5 \
    DB_TIMEZONE=UTC


EXPOSE 8000

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]