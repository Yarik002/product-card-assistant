FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY card_assistant ./card_assistant

EXPOSE 8000
CMD ["uvicorn", "card_assistant.web:app", "--host", "0.0.0.0", "--port", "8000"]
