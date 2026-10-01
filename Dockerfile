FROM python:3.13-slim
WORKDIR /app
COPY server.py .
ENV PYTHONUNBUFFERED=1
CMD ["python", "server.py"]
