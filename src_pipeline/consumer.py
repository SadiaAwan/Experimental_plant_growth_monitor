import random 
import time
from utils.connect_postgres import query_db

def simulate_temp():
    temp = round(random.uniform(10,30), 2)
    return temp

if __name__ == "__main__":
    #step 1- create a table in timescaledb
    query_db("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            time TIMESTAMPTZ NOT NULL,
            temperature DOUBLE PRECISION
        )
    """)

    #step 2- generate a series of temp
    while True:
        temp = simulate_temp()
        print(temp)
        time.sleep(.5)

        #step 3- insert values to the table
        query_db(
            f"""
            INSERT INTO sensor_readings
                (time, temperature)
            VALUES (NOW(),{temp})
            """)