FROM python:3.9-slim

WORKDIR /app
COPY . /app

RUN chmod +x main.py

# ENV IP_ADDRESS=192.168.1.100
# ENV PORT=13013
# ENV TARGET_PWR=10

CMD ["python", "main.py"]
