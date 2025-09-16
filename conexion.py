import mysql.connector

class DataBase:
    def __init__(self):
        self.connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="0412",
            database="la_burga_al_corte"
        )
        self.cursor = self.connection.cursor()






