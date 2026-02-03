FROM python:3.12-slim

WORKDIR /app

# 基础依赖（使用国内 Debian 源，加速构建，兼容无 sources.list 的情况）
RUN if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g; s/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libstdc++6 \
    libgomp1 \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app

# 镜像瘦身：容器中只保留 Linux 版 Rapfi，引擎的 Windows / macOS 版本删除
RUN rm -f Rapfi-engine/pbrain-rapfi-windows-* Rapfi-engine/pbrain-rapfi-macos-apple-silicon || true && \
    chmod +x Rapfi-engine/pbrain-rapfi-linux-clang-* || true

# 安装 Python 依赖（使用国内 PyPI 源）
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

EXPOSE 8801

ENV PYTHONUNBUFFERED=1

# 启动 FastAPI 应用（使用 python app.py，便于直接看到错误日志）
CMD ["python", "app.py"]


