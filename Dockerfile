FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 创建日志目录
RUN mkdir -p logs

# 暴露 Web 端口
EXPOSE 11021

# 启动命令
CMD ["python", "-m", "src.main"]
