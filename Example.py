from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

options = Options()
options.add_argument('--headless')
options.headless = True  # Запуск в безголовом режиме

# Используйте webdriver-manager для установки geckodriver
service = Service('geckodriver')
print(1)
driver = webdriver.Firefox(service=service)
print(2)

# Открытие страницы Google
driver.get("https://www.google.com")

# Вывод заголовка страницы
print("Заголовок страницы:", driver.title)

# Закрытие драйвера
driver.quit()
