# Base image do Playwright
FROM mcr.microsoft.com/playwright/python:v1.43.0

# Define o diretório de trabalho
WORKDIR /app

# Copia todos os arquivos do projeto para dentro do container
COPY . /app

# Instala as dependências (incluindo o uvicorn)
RUN pip install --upgrade pip \
  && pip install -r requirements.txt

# Expõe a porta que o FastAPI (Uvicorn) vai utilizar
EXPOSE 8000

# Comando para iniciar a aplicação FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
