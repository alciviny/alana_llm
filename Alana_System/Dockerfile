FROM python:3.10-slim

# Evita a criação de arquivos .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalação de dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- OTIMIZAÇÃO: Instala primeiro as bibliotecas gigantes ---
# Isso cria uma camada de cache que só é invalidada se as versões mudarem
RUN pip install --no-cache-dir \
    torch \
    sentence-transformers \
    llama-cpp-python \
    openai-whisper \
    scipy \
    numpy \
    matplotlib

# --- Instala o restante das dependências ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Baixa modelos spaCy (também cacheado) ---
RUN python -m spacy download en_core_web_sm && \
    python -m spacy download pt_core_news_sm

# Copia o código (durante o desenvolvimento usaremos volumes para ser instantâneo)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "bridge:app", "--host", "0.0.0.0", "--port", "8000"]
