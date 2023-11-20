import sqlite3

# Function to create the database schema
def create_schema():
    connection = sqlite3.connect('logs.db')
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT,
            message TEXT,
            resourceId TEXT,
            timestamp TEXT,
            traceId TEXT,
            spanId TEXT,
            commit TEXT,
            parentResourceId TEXT
        )
    ''')

    connection.commit()
    connection.close()

    print("Database 'logs.db' has been created.")

if __name__ == '__main__':
    create_schema()
