FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY meridian ./meridian
COPY sql ./sql
RUN useradd --system --uid 10001 meridian
USER meridian
CMD ["python", "-m", "meridian.service"]
