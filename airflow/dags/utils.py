import os
from airflow.hooks.S3_hook import S3Hook
from airflow.hooks.postgres_hook import PostgresHook
import psycopg2
from urllib.parse import urlencode
import requests
import pandas as pd
import json
import googleplaces


# API key for accesing google geocoding and places API
API_KEY = 'AIzaSyDgyLveFYJPhspb766HS1k6_aEYg-7QvyU'


def local_to_s3(
    bucket_name: str, key: str, file_name: str, remove_local: bool = False) -> None:
    s3 = S3Hook()
    s3.load_file(filename=file_name, bucket_name=bucket_name, replace=True, key=key)
    if remove_local:
        if os.path.isfile(file_name):
            os.remove(file_name)
            
def extract_zipcodes(bucket_name: str, key: str) -> None:
    s3 = S3Hook()
    sales=s3.read_key(key=key,bucket_name=bucket_name)
    sales=pd.DataFrame(sales)
    sales['zipcode']= sales['zipcode'].map(lambda x: str(x))
    z= pd.DataFrame(sales['zipcode'].unique())
    z.to_csv('zipcode.csv', index=False, header=False)
    

def extract_places(zipcode: list) -> None:
    
    all_zip_places = {}
    
    for zp in zipcode:
        client = googleplaces.GooglePlaces(api_key=API_KEY, zipcode=zp)
        all_places= {}
        keywords = ["healthcare", "transit", "entertainment"]
        for kw in keywords:
            all_places.update({'category':kw,'cat_places':client.extract_places(keyword=kw)})
        all_zip_places.update({'zipcode':zp,'places':all_places})
        
    with open('all_zip_places.json', 'w') as output_file:
        json.dump(all_zip_places, output_file)
        

def run_redshift_external_query(qry: str) -> None:
    rs_hook = PostgresHook(postgres_conn_id="redshift")
    rs_conn = rs_hook.get_conn()
    rs_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    rs_cursor = rs_conn.cursor()
    rs_cursor.execute(qry)
    rs_cursor.close()
    rs_conn.commit()
