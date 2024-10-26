FROM python:3.9-slim

WORKDIR /app
COPY . /app

RUN chmod +x main.py

RUN pip install flask

ENV API_KEY=your_api_key

CMD ["python", "main.py"]
