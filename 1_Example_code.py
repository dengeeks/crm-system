import re

client_response = "text , 4- 5"

# Проверяем наличие слова "стоп" или "STOP"
if re.search(r'\b(стоп|stop)\b', client_response, re.IGNORECASE):
    print("STOP detected!")
else:
    # Убираем пробелы для удобства обработки
    client_response_cleaned = re.sub(r'\s+', '', client_response)

    # Проверяем некорректные оценки (например, с запятыми)
    if re.search(r'\d[,\.]\d', client_response_cleaned):
        print(client_response_cleaned)
        print("Некорректный формат оценки, такие оценки не принимаются")
    else:
        # Оставляем только цифры 1-5, игнорируя все остальное
        client_response_cleaned = re.sub(r'[^1-5]', '', client_response_cleaned)

        # Проверяем количество уникальных оценок
        unique_grades = set(client_response_cleaned)  # Множество уникальных оценок

        if len(unique_grades) > 1:
            print("Некорректный ввод: указано несколько оценок")
        elif len(unique_grades) == 1:
            grade = unique_grades.pop()  # Получаем единственную оценку

            # Пример логики для ответа на оценки
            if grade == "5":
                print("Отличная оценка: 5 звёзд!")
            else:
                print("Низкая оценка!")
        elif len(client_response_cleaned) == 0:
            print("Оценка не указана, повторяем запрос!")
