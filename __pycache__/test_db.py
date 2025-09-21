import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="0412",
        database="la_burga_al_corte"
    )
    cur = conn.cursor()
    cur.execute("SHOW TABLES;")
    print("✅ Conexión exitosa. Tablas en la base de datos:")
    for row in cur.fetchall():
        print("-", row[0])
    conn.close()
except mysql.connector.Error as e:
    print("❌ Error al conectar:", e)
