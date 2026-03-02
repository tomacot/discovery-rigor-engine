# Discovery Rigor Engine — Docker image
#
# Used for two deployment targets:
#   1. Streamlit UI on AWS App Runner (CMD below)
#   2. LangGraph agent on Bedrock AgentCore Runtime (CMD overridden by AgentCore)
#
# Build: docker build -t discovery-rigor .
# Run locally: docker run -p 8501:8501 -e AWS_REGION=us-east-1 discovery-rigor

FROM python:3.11-slim

# Non-root user for security
RUN groupadd --gid 1001 app && useradd --uid 1001 --gid app --shell /bin/bash --create-home app

WORKDIR /app

# Install dependencies first (cached layer unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY ui/ ./ui/
COPY data/ ./data/
COPY app.py .

# Streamlit config — headless mode for container environments
RUN mkdir -p .streamlit
COPY .streamlit/config.toml .streamlit/config.toml

RUN chown -R app:app /app
USER app

EXPOSE 8501

# Health check for App Runner
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

# Default: run Streamlit UI
# AgentCore Runtime overrides CMD to run the agent handler
CMD ["python", "-m", "streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
