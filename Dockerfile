FROM python:3.9-slim

WORKDIR /app
COPY . /app

RUN chmod +x main.py

RUN pip install flask

CMD ["python", "main.py"]
