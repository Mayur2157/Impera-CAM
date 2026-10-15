FROM python:3.12-slim

WORKDIR /app

# System deps for pdfplumber page rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock

# CPU OCR (slow, for occasional scans): docker build --build-arg OCR=1 .
# GPU OCR uses Dockerfile.gpu instead.
ARG OCR=0
COPY requirements-ocr.txt .
RUN if [ "$OCR" = "1" ]; then \
        pip install --no-cache-dir paddlepaddle==3.3.0 -r requirements-ocr.txt; \
    fi

COPY . .

# uid 1000 matches the first user on a typical Linux VM, so the bind-mounted
# ./data/uploads and ./output stay writable
RUN useradd --uid 1000 --create-home bsx \
    && mkdir -p /data/uploads /data/output data/uploads output \
    && chown -R bsx /data /app/data /app/output
USER bsx

EXPOSE 8000

# One image, several roles: docker-compose.yml sets the command per service
# (migrate, api, worker-cpu, beat). Migrations are not run here: several API
# containers starting together would race on them.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
