FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    rsync \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY *.py .

# 创建日志目录
RUN mkdir -p /app/logs

# 默认运行主程序（可通过 docker exec 运行菜单）
CMD ["python", "-u", "main.py"]
