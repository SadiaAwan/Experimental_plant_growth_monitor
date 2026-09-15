import json
import os

import paho.mqtt.client as mqtt
import psycopg


# MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv(
    "MQTT_TOPIC",
    "nackademin/mlops25/pico/light",
)


# TimescaleDB / PostgreSQL
# Use DB_HOST=timescaledb when both services run in Docker Compose.
# Use DB_HOST=localhost when consumer.py runs directly on your computer.
DB_HOST = os.getenv("DB_HOST", "timescaledb")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "iot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def connect_database():
    """Connect to TimescaleDB and create the sensor table if needed."""
    connection = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=True,
    )

    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS light_sensor (
                time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                light DOUBLE PRECISION NOT NULL
            );
            """
        )
        cursor.execute(
            """
            SELECT create_hypertable(
                'light_sensor',
                'time',
                if_not_exists => TRUE
            );
            """
        )

    print("Connected to TimescaleDB")
    return connection


db_connection = None


def on_connect(client, userdata, flags, reason_code, properties):
    """Subscribe after MQTT connects or reconnects."""
    if reason_code == 0:
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to {MQTT_TOPIC}")
    else:
        print(f"MQTT connection failed: {reason_code}")


def on_message(client, userdata, message):
    """Receive a light value from Wokwi and save it in TimescaleDB."""
    global db_connection

    try:
        payload = message.payload.decode("utf-8")
        data = json.loads(payload)
        light_value = float(data["light"])

        print("Received:", data)

        if db_connection is None or db_connection.closed:
            db_connection = connect_database()

        with db_connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO light_sensor (light) VALUES (%s);",
                (light_value,),
            )

        print("Written to TimescaleDB:", light_value)

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        print(f"Invalid MQTT message: {error}")
    except psycopg.Error as error:
        print(f"TimescaleDB error: {error}")
        if db_connection is not None:
            db_connection.close()
        db_connection = None


def main():
    global db_connection

    db_connection = connect_database()

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    print(f"Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Stopping consumer")
    finally:
        client.disconnect()
        if db_connection is not None:
            db_connection.close()


if __name__ == "__main__":
    main()
