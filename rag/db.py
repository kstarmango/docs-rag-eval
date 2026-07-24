"""Postgres(pgvector) 연결 헬퍼. .env에서 접속정보 로드."""
import os

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

load_dotenv()


def connect():
    conn = psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "ragdb"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "ragpass"),
    )
    register_vector(conn)  # pgvector <-> numpy 자동 변환 등록
    return conn
