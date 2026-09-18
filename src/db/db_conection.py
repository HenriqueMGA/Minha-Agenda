import os
from contextlib import contextmanager

from dotenv import load_dotenv
from psycopg2.pool import ThreadedConnectionPool

load_dotenv()

db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")

connection_pool = ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host=db_host,
    port=db_port,
    database=db_name,
    user=db_user,
    password=db_password,
)


def close_pool():
    connection_pool.closeall()


@contextmanager
def get_connection():
    conexao = connection_pool.getconn()
    try:
        conexao.set_session(autocommit=False)
        cursor = conexao.cursor()
        cursor.execute("SET client_encoding = 'UTF8'")
        cursor.close()

        yield conexao
        conexao.commit()
    except Exception as e:
        conexao.rollback()
        print(f"ERRO: {e}")
        raise e
    finally:
        connection_pool.putconn(conexao)
