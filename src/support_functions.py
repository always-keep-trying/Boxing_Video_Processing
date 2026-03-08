from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from datetime import datetime
import numpy as np
import pytz
import re

def fmt_time(seconds: int):
    return f"{seconds//3600:02d}:{(seconds%3600)//60:02d}:{seconds%60:02d}"

def fmt_to_seconds(fmt_time_str: str):
    h, m, s = fmt_time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

def offset_fmt_time(fmt_time_str: str, offset_seconds:int | float, bounds=[0, np.inf]):
    sec = fmt_to_seconds(fmt_time_str)
    new_sec = sec+offset_seconds
    # apply lower bound
    new_sec = max(new_sec, min(bounds))
    # apply upper bound
    new_sec = min(new_sec, max(bounds))
    assert new_sec>=0, f'Time must be positive! can not offset {offset_seconds}s from {sec}s'
    return fmt_time(new_sec)


def gps_to_lat_lon(gps_location: str):
    # Parse the ISO 6709 location string e.g. "+47.6062-122.3321/"
    match = re.match(r'([+-]\d+\.\d+)([+-]\d+\.\d+)', gps_location)
    lat, lon = float(match.group(1)), float(match.group(2))
    return lat, lon


def guess_city_state(gps_location: str):

    if gps_location =='N/A':
        city = 'Unknown'
        state = ''
        print('Unknown location!')
    else:
        lat, lon = gps_to_lat_lon(gps_location)

        # Reverse geocode
        geolocator = Nominatim(user_agent="my_app")
        result = geolocator.reverse(f"{lat}, {lon}")

        address = result.raw['address']
        city = address.get('city') or address.get('town') or address.get('village')
        state = address.get('state')
        print(f"{city}, {state}")  # e.g. Seattle, Washington
    return city, state


def get_local_time(gps_location: str, creation_time: str) -> str:
    # Parse GPS
    lat, lon = gps_to_lat_lon(gps_location)

    # Get local timezone from coordinates
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=lat, lng=lon)
    local_tz = pytz.timezone(timezone_str)

    # Convert creation_time to local time
    dt_utc = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
    dt_local = dt_utc.astimezone(local_tz)

    return dt_local.strftime('%Y-%m-%d %I:%M%p')
