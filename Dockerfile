FROM python:3.12-slim
WORKDIR /MySenzBackend
ENV DJANGO_SETTINGS_MODULE=MySenzBackend.settings_docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*
    
COPY requirements.txt /MySenzBackend/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /MySenzBackend/
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
