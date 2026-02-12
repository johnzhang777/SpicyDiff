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

# Copy source code and entrypoint
COPY spicydiff/ ./spicydiff/
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run as non-root user for security
RUN adduser --disabled-password --gecos "" --uid 1001 spicydiff
USER spicydiff

ENTRYPOINT ["/app/entrypoint.sh"]
