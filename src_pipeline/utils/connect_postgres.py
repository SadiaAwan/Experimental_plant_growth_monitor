import os
import time

import psycopg


DB_HOST = os.getenv("DB_HOST", "timescaledb")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "plant_monitor")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")


def connect_database(max_attempts: int = 10, wait_seconds: int = 3):
    """
    Connect to TimescaleDB.

    The retry loop is useful because the consumer container may start
    before TimescaleDB is completely ready.
    """

    for attempt in range(1, max_attempts + 1):
        try:
            connection = psycopg.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                autocommit=True,
            )

            print("Connected to TimescaleDB")
            return connection

        except psycopg.OperationalError as error:
            print(
                f"Database connection attempt "
                f"{attempt}/{max_attempts} failed: {error}"
            )

            if attempt == max_attempts:
                raise

            time.sleep(wait_seconds)


def create_sensor_table(connection):
    """
    Enable TimescaleDB and create the table and hypertable.
    """

    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE EXTENSION IF NOT EXISTS timescaledb;"
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS plant_sensor_readings (
                time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                moisture DOUBLE PRECISION NOT NULL,
                distance DOUBLE PRECISION NOT NULL,
                plant_height DOUBLE PRECISION NOT NULL,
                growth DOUBLE PRECISION NOT NULL
            );
            """
        )

        cursor.execute(
            """
            SELECT create_hypertable(
                'plant_sensor_readings',
                'time',
                if_not_exists => TRUE
            );
            """
        )

    print("Table plant_sensor_readings is ready")