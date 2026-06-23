FROM python:3.11-slim

# 安装系统依赖（MySQL client + Playwright 依赖）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件（利用 Docker 层缓存）
COPY requirements.docker.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright Chromium 浏览器（仅安装 chromium，不安装 firefox/webkit）
RUN python -m playwright install chromium --with-deps

# 复制后端代码和配置
COPY backend/ ./backend/
COPY config.yaml ./config.yaml

# 创建必要目录
RUN mkdir -p /app/backend/data/prompts \
             /app/backend/data/chromadb \
             /app/backend/data/uploads

WORKDIR /app

EXPOSE 11528

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "11528", "--workers", "2"]
