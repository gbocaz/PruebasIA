FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY entrypoint.sh .
RUN chmod 755 /app/entrypoint.sh
RUN mkdir -p /app/data/packages
ENV DATABASE_URL=sqlite:////app/data/ticcontrol.db
EXPOSE 8000
CMD ["/app/entrypoint.sh"]
