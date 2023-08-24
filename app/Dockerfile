FROM python:3.11.2-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
COPY parse_faculties.py .
COPY parse_groups.py .
COPY parse_group_schedule.py .
CMD ["python", "main.py"]