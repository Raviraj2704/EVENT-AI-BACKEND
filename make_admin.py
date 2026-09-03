import sqlite3

conn = sqlite3.connect('eventai.db')
cursor = conn.cursor()

cursor.execute("UPDATE users SET role = 'admin' WHERE email = 'ravirajapanthulu@gmail.com'")
conn.commit()
conn.close()

print("FORCED ADMIN SUCCESS!")