FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/uploads /app/staticfiles

COPY entrypoint.sh /entrypoint.sh
# Retire les retours chariot (\r) au cas ou le fichier aurait ete checkout
# avec des fins de ligne Windows (CRLF) : un shebang "#!/bin/sh\r" fait
# echouer l'exec avec "no such file or directory" alors que le fichier
# existe bel et bien.
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
