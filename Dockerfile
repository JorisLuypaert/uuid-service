# Gebruik een lichte Python base image
FROM python:3.11-slim

# Zet werkdirectory
WORKDIR /app

# Kopieer requirements
COPY requirements.txt .

# Installeer dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Kopieer de rest van de code
COPY . .

# Expose de Render-poort
EXPOSE 10000

# Start FastAPI via uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]