FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml README.md ./
COPY ec2_health_monitor ./ec2_health_monitor

RUN python -m pip install --no-cache-dir .

USER app

ENTRYPOINT ["ec2-health"]
CMD ["--json"]

