'''Logs sensor values from a serial port to bit.io.

This implementation specifically logs air quality data from an SDS011 optical
sensor to a cloud Postgres database on bit.io using a simple Python program
that can run on a Raspberry Pi.

However, this pattern can be easily adapted for any similar IoT logging use-case
where a byte stream can be parsed for values that need to be logged to a
database.

This module includes extra comments to support a related tutorial.
'''


from datetime import datetime
from collections import defaultdict
import logging
from logging.handlers import RotatingFileHandler
import os
import serial

import bitdotio
from dotenv import load_dotenv
import yaml

import time
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus
from bme280 import BME280



# Load environment variables
load_dotenv()
BITDOTIO_API_KEY = os.getenv('BITDOTIO_API_KEY')


# Logging setup
log_file = 'log.out'
log_formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler = RotatingFileHandler(log_file, mode='a', maxBytes=20*1024**2, 
                                 backupCount=1, encoding=None, delay=0)
handler.setFormatter(log_formatter)
handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)


def parse_value(data, byte_order, start_byte, num_bytes, scale=None):
    """Returns an int from a sequence of bytes.

    Scale is an optional argument that handles decimals encoded as int.
    
    Parameters
    ----------
    data : bytes
        A sequence of bytes for one full sensor message
    byte_order : str, optional
        Endianness of the bytes, 'little' (default) or 'big'.
    start_byte : int
        Start byte of the parsed value in the message
    num_bytes : int
        Number of bytes in the parsed value.
    scale : float, optional
        Factor to scale the parsed value by, default none

    Returns 
    ----------
    int
    """
    value = data[start_byte: start_byte + num_bytes]
    value = int.from_bytes(value, byteorder=byte_order)
    value = value * scale if scale else value
    return value

def get_bme280_sensor_reading(bme280, config):
    record = {'location': config['location']}
    record['measurements'] = {}
    record["measurements"]["temp_in_c"]= bme280.get_temperature()
    record["measurements"]["pressure"] = bme280.get_pressure()
    record["measurements"]["humidity"] = bme280.get_humidity()
    record['datetime'] = str(datetime.utcnow())
    return record

def get_air_quality_reading(ser, config):
    record = {'location': config['location']}
    record['measurements'] = {}
    sample = ser.read(CONFIG['message_length']
    record['sensor_id'] = parse_value(sample, config['byte_order'], *config['sensor_id'])

    for measurement, parse_args in config['measurements'].items():
        record["measurements"][measurement] = parse_value(sample, config['byte_order'], *parse_args)
    record['datetime'] = str(datetime.utcnow())
    return record




def execute_sql(bitdotio, sql, params=None):
    """Run arbitrary sql with parameters on bit.io.
    
    Parameters
    ----------
    bitdotio : _Bit object
        bit.io connection client.
    sql : str
        A SQL statement with optional parameters.
    params : list, optional
        Parameters for psycopg2 escaped interpolation, all as str type
    ----------
    """
    try:
        conn = bitdotio.get_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        cur.close()
        conn.commit()
    except Exception as e:
        logger.exception('A query error occurred')
        raise e
    finally:
        if conn is not None:
            conn.close()

def insert_record(bitdotio, record, qualified_table):
    """Inserts a single sensor measurement record.
    
    Parameters
    ----------
    bitdotio : _Bit object
        bit.io connection client.
    record : list
        The record as a list of str representations.
    qualified_table: str
        The schema qualified table to upload to.
    ----
    """
    sql = f'INSERT INTO {qualified_table} '
    sql += 'VALUES (' + ', '.join(['%s'] * len(record)) + ');'
    execute_sql(bitdotio, sql, record)


def main():
    # Load config from file
    with open('config.yaml', 'r') as f:
        CONFIG = yaml.safe_load(f)

    # Schema-qualified upload table
    qualified_table = f'''"{CONFIG['repo_owner']}/{CONFIG['repo_name']}"."{CONFIG['table_name']}"'''

    # Construct a bitdotio client object
    bit = bitdotio.bitdotio(BITDOTIO_API_KEY)

    # Construct an interface to the USB serial port
    ser = serial.Serial(CONFIG['port_device'])
    i2c_addr = CONFIG['i2c_addr']

    # Initialise the BME280
    bus = SMBus(1)
    bme280 = BME280(i2c_dev=bus,i2c_addr=i2c_addr)

    # Construct a container for retrying failed uploads
    # This helps if you run into an occasional network (e.g. wifi, DNS) glitch
    upload_buffer = []
    
    while True:
        # Process terminates if upload buffer reaches limit
        if len(upload_buffer) > CONFIG['max_retries']:
            logger.error('Terminating process due to maximum upload failures.') 
            break
        # Read data from sensor for specified period
        samples = []
        for i in range(CONFIG['period']):
            bme_record = get_bme280_sensor_reading(bme280, config)
            aqi_record = get_air_quality_reading(ser, config)
            samples.append(aqi_record.update(bme_record))

        avg_record = {'location': CONFIG['location']}
        avg_record["measurements"] = defaultdict(float) 
        avg_record['datetime'] = str(datetime.utcnow())
        for sample in samples:
            for measurement in sample["measurements"]:
                avg_record["measurements"][measurement] = avg_record["measurements"][measurement] + sample["measurements"][measurement]
        for measurement in sample["measurements"]:
            avg_record["measurements"][measurement] = avg_record["measurements"][measurement] / CONFIG["period"]


        # average all the measurements

        # Process sample of data to create a record and add to upload buffer
        upload_buffer.append(avg_record)

        # Upload from buffer, if exception occurs, keep reading data and try later
        while upload_buffer:
            record = upload_buffer.pop()
            record_list = [record[col] for col in CONFIG['columns']]
            try:
                insert_record(bit, record_list, qualified_table)
                logger.info(f'RECORD UPLOADED: {record}')
            except Exception as e:
                upload_buffer.append(record)
                logger.exception('An upload error occurred.')
                break


if __name__ == '__main__':
    main()
