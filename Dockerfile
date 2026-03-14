FROM python:3.11-slim

WORKDIR /app

# Copy project
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command — override at runtime for specific pipelines
CMD ["python", "scripts/run_batch.py"]
