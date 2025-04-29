FROM mcr.microsoft.com/playwright/python:v1.43.0

WORKDIR /app
COPY . /app

# Instala dependências
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expõe a porta usada pelo Uvicorn
EXPOSE 8000

# Comando para rodar o app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]