from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import time

# Указываем путь к исполняемому файлу Firefox
firefox_binary = "/usr/bin/firefox"  # Замени на путь, который вернет команда 'which firefox'

# Устанавливаем опции для браузера (безголовый режим)
options = Options()
options.binary_location = firefox_binary
options.headless = True

# Указываем точный путь к geckodriver через объект Service
service = Service(executable_path='/var/www/www-root/data/www/3651259-is67937.twc1.net/instance/geckodriver')

# Запускаем Firefox с указанными параметрами
driver = webdriver.Firefox(service=service, options=options)

try:
    print("Открываем браузер в безголовом режиме...")
    # Переходим на сайт GitHub
    driver.get('https://github.com')
    print("Открыт сайт GitHub")

    # Подождем несколько секунд, чтобы все элементы загрузились
    time.sleep(3)

    # Получаем заголовок страницы
    title = driver.title
    print(f"Заголовок страницы: {title}")

    # Ищем элемент по ссылке "Sign up"
    sign_up_element = driver.find_element('link text', 'Sign up')
    print("Элемент 'Sign up' найден")

    # Выводим текст элемента
    print(f"Текст элемента: {sign_up_element.text}")

finally:
    # Закрываем браузер
    driver.quit()
    print("Браузер закрыт")
