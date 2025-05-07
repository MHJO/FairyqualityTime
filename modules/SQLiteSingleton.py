import sqlite3

class SQLiteSingleton:
    __instance = None

    def __new__(cls, db_path, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.connection = sqlite3.connect(db_path)
            cls.__instance.cursor = cls.__instance.connection.cursor()
        return cls.__instance

    def execute_query(self, query, params=None):
        if params is None:
            params = ()
        self.cursor.execute(query, params)
        self.connection.commit()
        return self.cursor.fetchall()

    def close(self):
        self.connection.close()


# # 사용 예시:
# if __name__ == "__main__":
#     db1 = SQLiteSingleton("example.db")
#     db2 = SQLiteSingleton("example.db")
#     # db1과 db2는 동일한 인스턴스입니다.
#     print(f"db1 is db2: {db1 is db2}")

#     # 간단한 쿼리 실행 예:
#     db1.execute_query("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
#     db1.execute_query("INSERT INTO test (name) VALUES (?)", ("Alice",))
#     result = db1.execute_query("SELECT * FROM test")
#     print(result)
#     db1.close()
