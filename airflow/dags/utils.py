import os
from airflow.hooks.S3_hook import S3Hook
from airflow.hooks.postgres_hook import PostgresHook
import psycopg2
from urllib.parse import urlencode
import requests


# API key for accesing google geocoding and places API
API_KEY = 'AIzaSyDgyLveFYJPhspb766HS1k6_aEYg-7QvyU'
DATA_TYPE = 'json'
# Defines the distance (in meters) within which to return place results
RADIUS = 1500
# Get all the healthcare,transit and entertainments available in the neighbourhood(zipcode)
PLACE_TYPE = ["healthcare", "transit", "entertainment"]


def _local_to_s3(
    bucket_name: str, key: str, file_name: str, remove_local: bool = False
) -> None:
    s3 = S3Hook()
    s3.load_file(filename=file_name, bucket_name=bucket_name, replace=True, key=key)
    if remove_local:
        if os.path.isfile(file_name):
            os.remove(file_name)


def run_redshift_external_query(qry: str) -> None:
    rs_hook = PostgresHook(postgres_conn_id="redshift")
    rs_conn = rs_hook.get_conn()
    rs_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    rs_cursor = rs_conn.cursor()
    rs_cursor.execute(qry)
    rs_cursor.close()
    rs_conn.commit()


# geocoding api

def extract_lat_lang(postalcode, data_type='json'):
    endpoint = f"https://maps.googleapis.com/maps/api/geocode/{DATA_TYPE}"
    params = {"address": postalcode, "key": API_KEY}
    url_params = urlencode(params)
    url = f"{endpoint}?{url_params}"
    r = requests.get(url)
    if r.status_code not in range(200, 299):
        return {}
    return r.json()


def extract_places(zipcode):
    lat, lng = extract_lat_lang(zipcode)
    # lat, lng = 46.0878165, -64.7782313
    # places api
    places_endpoint="https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": API_KEY,
        "location": f"{lat},{lng}",
        "radius": RADIUS,
        "keyword": PLACE_TYPE
    }
    params_encoded = urlencode(params)
    places_url = f"{places_endpoint}?{params_encoded}"
    result = requests.get(places_url)
    return result.json()


def extract_neighborhood(zipcode_list):
    for code in zipcode_list:
        places = extract_places(code)
        _local_to_s3(places)
