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
import logging
from logging.handlers import RotatingFileHandler
import os
import serial

import bitdotio
from dotenv import load_dotenv
import yaml


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
    start_byte : int
        Start byte of the parsed value in the message
    num_bytes : int
        Number of bytes in the parsed value.
    byte_order : str, optional
        Endianness of the bytes, 'little' (default) or 'big'.
    scale_denom : float, optional
        Factor to scale the parsed value by, default none

    Returns 
    ----------
    int
    """
    value = data[start_byte: start_byte + num_bytes]
    value = int.from_bytes(value, byteorder=byte_order)
    value = value * scale if scale else value
    return value


def execute_sql(bitdotio, sql, params=None):
    """Run arbitrary sql with parameters on bit.io.
    
    Parameters
    ----------
    bitdotio : _Bit object
        bit.io connection client.
    sql : str
        A SQL statement with optional parameters.
    params : list, optional
        Parameters for psycopg2 escaped interpolation
    ----------
    """
    try:
        conn = bitdotio.get_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        cur.close()
        conn.commit()
    except Exception as e:
        logger.exception('An error occurred')
        raise e
    finally:
        if conn is not None:
            conn.close()


def create_record(sample, CONFIG):
    """Run arbitrary sql with parameters on bit.io.
    
    Parameters
    ----------
    bitdotio : _Bit object
        bit.io connection client.
    sql : str
        A SQL statement with optional parameters.
    params : list, optional
        Parameters for psycopg2 escaped interpolation
    ----
    """
    record = {'location': CONFIG['location']}
    record['sensor_id'] = parse_value(sample[0], *CONFIG['sensor_id'])
    record['datetime'] = str(datetime.utcnow())
    for measurement, parse_args in CONFIG['measurements'].items():
        meas_sum = sum([parse_value(x, CONFIG['byte_order'], *parse_args) for x in sample])
        record[measurement] = meas_sum / CONFIG['period']
    return record



def insert_record(bitdotio, record, fully_qualified):
    """Inserts a single sensor measurement record.
    
    Parameters
    ----------
    bitdotio : _Bit object
        bit.io connection client.
    record : list
        The record.
    config : list, optional
        Parameters for psycopg2 escaped interpolation
    ----
    """
    sql = f'INSERT INTO {fully_qualified} '
    sql += 'VALUES (' + ', '.join(['%s'] * len(record)) + ');'
    execute_sql(bitdotio, sql, record)


def main():
    # Load config from file
    with open('config.yaml', 'r') as f:
        CONFIG = yaml.safe_load(f)

    # Schema-qualified upload table
    fully_qualified = f'''"{CONFIG['repo_owner']}/{CONFIG['repo_name']}"."{CONFIG['table_name']}"'''

    # Construct a bitdotio client object
    bit = bitdotio.bitdotio(BITDOTIO_API_KEY)

    # Construct an interface to the USB serial port
    ser = serial.Serial(CONFIG['port_device'])

    # Construct a container for retrying failed uploads
    # This helps if you run into an occasional network (e.g. wifi, DNS) glitch
    upload_buffer = []
    
    while True:
        # Process terminates if upload buffer reaches limit
        if len(upload_buffer) > CONFIG['max_retries']:
            logger.error('Terminating process due to maximum upload failures.') 
            break
        # Read data from sensor for specified period
        sample = [ser.read(CONFIG['message_length']) for i in range(CONFIG['period'])]
        # Process sample of data to create a record and add to upload buffer
        upload_buffer.append(create_record(sample, CONFIG))
        # Upload from buffer, if exception occurs, keep reading data and try later
        while upload_buffer:
            record = upload_buffer.pop()
            record_list = [record[col] for col in CONFIG['columns']]
            try:
                insert_record(bit, record_list, CONFIG)
                logger.info(f'RECORD UPLOADED: {record}')
            except Exception as e:
                upload_buffer.append(record)
                logger.exception('An upload error occurred.')
                break


if __name__ == '__main__':
    main()
