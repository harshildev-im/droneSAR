import mysql.connector 

class Database:
    def __init__(self):
        self.conn = None 
        self.cursor = None 
    @staticmethod
    def log_file(text):
        file = open('logs.txt' , 'a')
        file.write(f'{text}\n')
        file.close()
    def connect_db(self , name = 'project_wright_final'):
        try:
            self.conn = mysql.connector.connect(user='root' , passwd='harshiljain' , database=name)
            self.cursor = self.conn.cursor()
            text = "connected to database"
            Database.log_file(text)
            return True 
        except Exception as e:
            Database.log_file(e)
            return False
    def disconnect_db(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            self.cursor = None
            Database.log_file("Disconnected from database")
    def create_user(self, userid, password):
        try:

            # Validate User ID first
            if not userid.replace("_", "").isalnum():
                return False, "Invalid User ID."

            if len(userid) > 50:
                return False, "User ID cannot be longer than 50 characters."

            # Check if application user already exists
            self.cursor.execute(
                "SELECT userid FROM users WHERE userid = %s",
                (userid,)
            )

            if self.cursor.fetchone():
                return False, "User ID already exists."

            # Create application user
            self.cursor.execute(
                """
                INSERT INTO users (userid, password)
                VALUES (%s, %s)
                """,
                (userid, password)
            )

            # Create MySQL account for localhost

            self.conn.commit()
            self.cursor.execute(f'create database {userid}')
            Database.log_file(
                f"Created user: {userid}"
            )

            return True, "Account created successfully."

        except Exception as e:

            self.conn.rollback()

            Database.log_file(
                f"Create user error: {e}"
            )

            return False, "Could not create account."

    def authenticate_user(self, userid, password):
        try:
            self.cursor.execute(
                """
                SELECT userid
                FROM users
                WHERE userid = %s AND password = %s
                """,
                (userid, password)
            )
            user = self.cursor.fetchone()
            if user:
                Database.log_file(
                    f"Successful login: {userid}"
                )
                return True
            Database.log_file(
                f"Failed login: {userid}"
            )
            return False
        except Exception as e:
            Database.log_file(
                f"Authentication error: {e}"
            )
            return False