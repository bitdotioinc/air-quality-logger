# pi-bitdotio-air

A minimal air quality data logger using Python and bit.io.

## Setup

- Add a .env with your own bit.io API key as `BITDOTIO_API_KEY`
- Update the YAML to point to your desired repo/table
- Create environment
    - `python3 -m venv venv`<br>
    - `source venv/bin/activate`<br>
    - `python3 -m pip install --upgrade pip -r requirements.txt`<br>


## Run
`python pi_bitdotio_air.py`
