import os
import mysql.connector
from mysql.connector import Error
from PyQt5.QtWidgets import QMessageBox

# ---------------- Config DB ----------------
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', '0412'),
    'database': os.environ.get('DB_NAME', 'la_burga_al_corte')
}

# ---------------- Conexión DB ----------------
def db_connect():
    try:
        cn = mysql.connector.connect(**DB_CONFIG)
        if cn.is_connected():
            return cn
    except Error as e:
        QMessageBox.critical(None, "Error DB", f"No se pudo conectar a la base de datos:\n{e}")
    return None
