FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

RUN python -m spacy download en_core_web_sm

CMD gunicorn --bind 0.0.0.0:5000 --timeout 120 app:app 