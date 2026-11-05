FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY product_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Standalone service: it deliberately does not install the shared/ package.
COPY product_api/app/ /srv/app/

RUN useradd --system --uid 10001 --no-create-home productapi
USER 10001

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
