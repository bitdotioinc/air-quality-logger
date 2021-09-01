# air-quality-logger

A minimal air quality data logger using Python and Postgres on bit.io.

## Purpose 

This repo demonstrates how to log sensor data to a cloud database using Python
and Postgres hosted on bit.io. 

This particular demonstration application is logging air quality sensor data
from an outdoor Raspberry Pi Zero W (using home wifi). The sensor is an SDS011
which has received good reviews for the low-cost optical sensor class of air 
quality monitoring devices. 

You can read the sensor specification sheet [here](http://www.inovafitness.com/en/a/chanpinzhongxin/95.html).

## Setup

1. Clone this repository  
```bash
git clone https://github.com/bitdotioinc/air-quality-logger.git
```
2. Navigate to the directory root  
```bash
cd air-quality-logger
```
3. Add a `.env` text file with your own [bit.io API key](https://docs.bit.io/docs/using-python-bitdotio) as `BITDOTIO_API_KEY`  
```bash
touch .env & echo 'BITDOTIO_API_KEY=<INSERT_YOUR_API_KEY_HERE>'
```
4. Update `repo_owner`, `repo_name`, and `table_name` in the `config.yaml` file to point to your desired repo/table on bit.io.<br><br>
5. Create a virtual environment and install the required packages from `requirements.txt`
```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip -r requirements.txt
```
6. Run the logging script
```bash
python air_quality_logger.py
```

## Repo contents

### `air_quality_logger.py`
The main script to run for data logging.

### `config.yaml`
Configures various settings like upload destination, record schema, sensor data encoding, upload frequency, and more.

### `requirements.txt`
Dependencies for `air_quality_logger.py`

### `schema.sql`
Statement for creating a compatible database table.
