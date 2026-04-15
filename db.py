import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="W7301@jqir#",
        database="smart_restaurant"
    )