FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

COPY src/requirements.txt .

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libpq-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install uv
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY . .

ENV LANGCHAIN_TRACING_V2=true \
    LANGCHAIN_ENDPOINT="https://api.smith.langchain.com" \
    LANGCHAIN_PROJECT="default"

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
