FROM python:3.9-slim

LABEL maintainer="SpicyDiff Team"
LABEL description="LLM-powered code review with personality"

# Prevent Python from buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY spicydiff/ ./spicydiff/

ENTRYPOINT ["python", "-m", "spicydiff.main"]
