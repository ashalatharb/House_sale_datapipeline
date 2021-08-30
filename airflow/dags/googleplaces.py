import requests
from urllib.parse import urlencode


class GooglePlaces(object):
    lat = None
    lng = None
    data_type = 'json'
    zipcode = None
    api_key = None

    def __init__(self, api_key=None, zipcode=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if api_key is None:
            raise Exception("API key is required")
        self.api_key = api_key
        self.zipcode = zipcode
        if self.zipcode is not None:
            self._extract_lat_lng()

    def _extract_lat_lng(self, location=None):
        loc_query = self.zipcode
        if location is not None:
            loc_query = location
        endpoint = f"https://maps.googleapis.com/maps/api/geocode/{self.data_type}"
        params = {"address": loc_query, "key": self.api_key}
        url_params = urlencode(params)
        url = f"{endpoint}?{url_params}"
        r = requests.get(url)
        if r.json()['status'] != "OK":
            return {}
        latlng = {}
        try:
            latlng = r.json()['results'][0]['geometry']['location']
        except:
            pass  # TODO
        lat, lng = latlng.get("lat"), latlng.get("lng")
        self.lat = lat
        self.lng = lng
        print(self.lat,self.lng)
        return lat, lng

    def extract_places(self, keyword,location=None):
        lat, lng = self.lat, self.lng
        if location is not None:
            lat, lng = self._extract_lat_lng(location=location)
        endpoint = f"https://maps.googleapis.com/maps/api/place/nearbysearch/{self.data_type}"
        params = {
            "key": self.api_key,
            "location": f"{lat},{lng}",
            "radius": 1500,
            "keyword": keyword  # ["healthcare", "transit", "entertainment"]
        }
        params_encoded = urlencode(params)
        places_url = f"{endpoint}?{params_encoded}"
        r = requests.get(places_url)
        if r.json()['status'] != "OK":
            return {}
        return r.json()['results']
