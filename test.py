import pandas as pd
import sqlite3

connection = sqlite3.connect('my_db.db')

query = 'SELECT * FROM products'

df = pd.read_sql(query, connection)

connection.close()

print(df)