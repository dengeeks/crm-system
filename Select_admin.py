from Env_Config import Database_setting
import psycopg2

connect = psycopg2.connect(
    user=Database_setting['user'],
    password=Database_setting['password'],
    host=Database_setting['host'],
    port=Database_setting['port'],
    database=Database_setting['database']
)
cursor = connect.cursor()
username = "General_admin"
role = "General_admin"
password = "General_admin_password"
try:
    cursor.execute("INSERT INTO Admins (username, password, role) VALUES (%s, %s, %s);", (username, password, role))
    connect.commit()
    print("Да")
except Exception as ex:
    print(f"ERROR : {ex}")