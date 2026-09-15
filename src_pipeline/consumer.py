import json
import os

import paho.mqtt.client as mqtt
import psycopg

from utils.connect_postgres import (
    connect_database,
    create_sensor_table,
)


# ---------------------------------------------------------
# MQTT settings
# ---------------------------------------------------------

MQTT_BROKER = os.getenv(
    "MQTT_BROKER",
    "broker.hivemq.com",
)

MQTT_PORT = int(
    os.getenv("MQTT_PORT", "1883")
)

MQTT_TOPIC = os.getenv(
    "MQTT_TOPIC",
    "nackademin/mlops25/pico/light",
)


database_connection = None


def get_number(data: dict, key: str) -> float:
    """
    Read and validate one numeric value from the MQTT message.
    """

    if key not in data:
        raise ValueError(f"Missing field: {key}")

    return float(data[key])


def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties,
):
    """
    Called when the consumer connects to the MQTT broker.
    """

    if reason_code == 0:
        client.subscribe(MQTT_TOPIC)

        print("Connected to MQTT broker")
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"MQTT connection failed: {reason_code}")


def on_message(client, userdata, message):
    """
    Receive plant readings from Wokwi and save them
    in TimescaleDB.
    """

    global database_connection

    try:
        payload = message.payload.decode("utf-8")
        data = json.loads(payload)

        moisture = get_number(data, "moisture")
        distance = get_number(data, "distance")
        plant_height = get_number(data, "plant_height")
        growth = get_number(data, "growth")

        print("Received MQTT data:", data)

        if (
            database_connection is None
            or database_connection.closed
        ):
            database_connection = connect_database()
            create_sensor_table(database_connection)

        with database_connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO plant_sensor_readings (
                    moisture,
                    distance,
                    plant_height,
                    growth
                )
                VALUES (%s, %s, %s, %s);
                """,
                (
                    moisture,
                    distance,
                    plant_height,
                    growth,
                ),
            )

        print("Reading saved in TimescaleDB")

    except UnicodeDecodeError as error:
        print(f"MQTT message is not valid UTF-8: {error}")

    except json.JSONDecodeError as error:
        print(f"MQTT message is not valid JSON: {error}")

    except (ValueError, TypeError) as error:
        print(f"Invalid sensor data: {error}")

    except psycopg.Error as error:
        print(f"TimescaleDB error: {error}")

        if database_connection is not None:
            database_connection.close()

        database_connection = None


def main():
    global database_connection

    database_connection = connect_database()
    create_sensor_table(database_connection)

    mqtt_client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="plant-monitor-consumer",
    )

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    print(
        f"Connecting to MQTT broker "
        f"{MQTT_BROKER}:{MQTT_PORT}"
    )

    try:
        mqtt_client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            keepalive=60,
        )

        mqtt_client.loop_forever()

    except KeyboardInterrupt:
        print("Stopping MQTT consumer")

    finally:
        mqtt_client.disconnect()

        if database_connection is not None:
            database_connection.close()


if __name__ == "__main__":
    main()