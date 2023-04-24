import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root'
)
c = conn.cursor()
c.execute('CREATE DATABASE IF NOT EXISTS quotes')
c.execute('USE quotes')
c.execute('CREATE TABLE IF NOT EXISTS quotes (id INT AUTO_INCREMENT PRIMARY KEY, text VARCHAR(512) NOT NULL UNIQUE, author TEXT NOT NULL)')
conn.close()