import sqlite3

# Подключаемся к базе данных
conn = sqlite3.connect('рейтинг.db')

# Создаем таблицу, если ее нет
conn.execute('''CREATE TABLE IF NOT EXISTS abiturients
             (ID INTEGER PRIMARY KEY AUTOINCREMENT,
             NAME TEXT NOT NULL,
             SCORE INTEGER NOT NULL);''')

# Получаем от пользователя количество баллов
user_score = int(input("Введите количество баллов: "))

# Ищем место пользователя в рейтинге
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM abiturients WHERE SCORE > ?", (user_score,))
place = cursor.fetchone()[0] + 1

# Добавляем данные пользователя в базу данных
name = input("Введите имя: ")
cursor.execute("INSERT INTO abiturients (NAME, SCORE) VALUES (?, ?)", (name, user_score))
conn.commit()

# Выводим результат
print("Ваше место в рейтинге:", place)

# Закрываем соединение с базой данных
conn.close()
