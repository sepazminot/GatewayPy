FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
# Asegúrate de que uvicorn esté dentro de tu archivo requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY gateway.py .

# Exponer el puerto interno en el que escuchará Uvicorn
EXPOSE 8000

# NUEVO: Comando de arranque optimizado para controlar la concurrencia en producción
CMD ["uvicorn", "gateway:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]