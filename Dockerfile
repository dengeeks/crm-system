FROM python:3.11-alpine

# Устанавливаем необходимые зависимости и браузер Firefox
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow

# Устанавливаем пакеты, включая Firefox и geckodriver
RUN apk update && apk add --no-cache \
    firefox \
    bash \
    curl \
    && rm -rf /var/cache/apk/*

# Загружаем geckodriver, который необходим для работы с Firefox в Selenium
RUN curl -sSL https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz | tar -xz -C /usr/local/bin

# Устанавливаем рабочую директорию и копируем файл с зависимостями
WORKDIR /app
COPY requirements.txt /app/

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы приложения
COPY . /app/

# Открываем порт для приложения
EXPOSE 5000

# Запускаем приложение (в данном случае инициализация базы данных и запуск приложения через gunicorn)
CMD ["sh", "-c", "python init_db.py && gunicorn -w 4 -b 0.0.0.0:5000 --timeout 600 Server:application"]
