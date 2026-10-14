FROM python:3.12-slim

WORKDIR /app

# System deps for PyMuPDF / pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# OCR deps are separate — uncomment in requirements-ocr.txt and
# rebuild with: docker build --build-arg OCR=1 -t impera-cam .
ARG OCR=0
COPY requirements-ocr.txt .
RUN if [ "$OCR" = "1" ]; then pip install --no-cache-dir -r requirements-ocr.txt; fi

COPY . .

# Create runtime dirs (volumes override these in production)
RUN mkdir -p data/uploads output

EXPOSE 8000

# Run Alembic migrations then start the server.
# Override with CMD in docker-compose to skip migrations during local dev.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
