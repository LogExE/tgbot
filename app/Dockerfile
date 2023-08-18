FROM python:3.11.2-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
COPY uniparse.py .
CMD ["python", "main.py"]