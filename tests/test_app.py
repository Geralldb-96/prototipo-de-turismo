import json
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from app import Handler, recommend, forecast

class RulesTest(unittest.TestCase):
    def test_boundary_and_priority(self):
        for wind in (0, 49.9, 50):
            self.assertTrue(any(a['outdoor'] for a in recommend(wind, 0)['activities']))
            self.assertIsNone(recommend(wind, 0)['safety_alert'])
        for wind in (50.01, 60, 120):
            for code in (0, 3, 61, 95):
                result = recommend(wind, code)
                self.assertFalse(any(a['outdoor'] for a in result['activities']))
                self.assertEqual(result['safety_alert']['code'], 'HIGH_WIND')
                self.assertTrue(result['activities'])

    def test_rain(self):
        self.assertFalse(any(a['outdoor'] for a in recommend(20, 61)['activities']))

    def test_bad_values(self):
        for wind in (-1, None, 'bad', float('nan'), float('inf')):
            with self.assertRaises(ValueError): recommend(wind, 0)
        with self.assertRaises(ValueError): recommend(20, 4)

    def test_provider_parsing(self):
        payload = {'hourly_units': {'wind_speed_10m': 'km/h'}, 'hourly': {'time': ['2099-01-01T00:00'], 'weather_code': [0], 'wind_speed_10m': [60]}}
        import io
        with patch('app.urlopen', return_value=io.StringIO(json.dumps(payload))):
            self.assertEqual(forecast(4, -74)['safety_alert']['code'], 'HIGH_WIND')
        payload['hourly_units']['wind_speed_10m'] = 'm/s'
        with patch('app.urlopen', return_value=io.StringIO(json.dumps(payload))):
            with self.assertRaises(ValueError): forecast(4, -74)

class HttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def test_demo(self):
        with urlopen(self.base + '/api/demo?wind=60&code=0') as response:
            data = json.load(response)
        self.assertTrue(data['simulated'])
        self.assertTrue(data['outdoor_blocked'])

    def test_invalid(self):
        for path in ('/api/recommendations?lat=999', '/api/demo?wind=NaN', '/api/demo?wind=2&wind=60'):
            with self.assertRaises(HTTPError) as result: urlopen(self.base + path)
            self.assertEqual(result.exception.code, 400)

    def test_provider_failure(self):
        with patch('app.forecast', side_effect=TimeoutError):
            with self.assertRaises(HTTPError) as result: urlopen(self.base + '/api/recommendations')
            self.assertEqual(result.exception.code, 503)
            data = json.load(result.exception)
            self.assertEqual(data['activities'], [])
            self.assertTrue(data['outdoor_blocked'])

if __name__ == '__main__': unittest.main()
