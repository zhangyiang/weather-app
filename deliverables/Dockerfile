# 聚合天气平台 - 容器镜像
# 构建：docker build -t weather-app ./deliverables
# 运行：docker run -p 8000:8000 -e PORT=8000 weather-app
FROM python:3.11-slim

# 安装 bcrypt 等可能需要的编译工具（多数有 wheel，保留以防万一）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖（利用 Docker 层缓存）
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 复制后端与前端静态资源（保持 ../html-prototype 相对路径有效）
COPY backend/ ./backend/
COPY html-prototype/ ./html-prototype/

WORKDIR /app/backend

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','8000')).read()" || exit 1

# Render 会注入 PORT 环境变量；本地默认 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
