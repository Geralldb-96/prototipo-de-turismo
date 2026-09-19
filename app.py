"""Microservicio académico de turismo. Python 3.10+, sin dependencias externas."""
import json
import math
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

ACTIVITIES = [
    {"id": "museo", "name": "Visitar un museo", "outdoor": False},
    {"id": "gastronomia", "name": "Taller de gastronomía en un local cerrado", "outdoor": False},
    {"id": "parque", "name": "Pasear por un parque", "outdoor": True},
    {"id": "recorrido", "name": "Recorrido cultural a pie", "outdoor": True},
]
VALID_CODES = {0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99}


def number(value, name, low, high):
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} debe ser numérico") from None
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f"{name} debe estar entre {low} y {high}")
    return result


def recommend(wind, code):
    wind = number(wind, "Viento", 0, 500)
    code = number(code, "Código meteorológico", 0, 99)
    if code not in VALID_CODES:
        raise ValueError("Código meteorológico no reconocido")
    # La política de seguridad tiene prioridad sobre el estado del cielo.
    blocked = wind > 50
    outdoor_weather = code in {0, 1, 2, 3}
    activities = [a.copy() for a in ACTIVITIES if not a["outdoor"] or (outdoor_weather and not blocked)]
    return {
        "wind_kmh": wind, "weather_code": int(code),
        "outdoor_blocked": blocked or not outdoor_weather,
        "safety_alert": {"code": "HIGH_WIND", "message": "Alerta de seguridad: viento superior a 50 km/h. Todas las actividades al aire libre están bloqueadas."} if blocked else None,
        "reason": "Viento superior a 50 km/h" if blocked else ("Clima no favorable para actividades al aire libre" if not outdoor_weather else "Puedes explorar planes al aire libre: no hay alerta por viento fuerte."),
        "activities": activities,
    }


def forecast(lat, lon):
    params = urlencode({"latitude": lat, "longitude": lon, "hourly": "weather_code,wind_speed_10m", "wind_speed_unit": "kmh", "timezone": "GMT", "forecast_days": 2})
    with urlopen("https://api.open-meteo.com/v1/forecast?" + params, timeout=10) as response:
        data = json.load(response)
    if data.get("hourly_units", {}).get("wind_speed_10m") != "km/h":
        raise ValueError("Unidad de viento inesperada")
    hourly = data["hourly"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i, timestamp in enumerate(hourly["time"]):
        if datetime.fromisoformat(timestamp) >= now:
            result = recommend(hourly["wind_speed_10m"][i], hourly["weather_code"][i])
            return dict(result, forecast_time=timestamp + "Z", source="Open-Meteo", simulated=False)
    raise ValueError("No hay pronóstico futuro disponible")


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        request = urlparse(self.path)
        if request.path == "/":
            data = Path(__file__).with_name("index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if request.path == "/health":
            return self.reply(200, {"status": "ok"})
        query = parse_qs(request.query, keep_blank_values=True)
        def param(key, default):
            values = query.get(key, [default])
            if len(values) != 1:
                raise ValueError(f"Parámetro repetido: {key}")
            return values[0]
        try:
            if request.path == "/api/demo":
                return self.reply(200, dict(recommend(param("wind", "60"), param("code", "0")), source="Simulación académica", simulated=True, forecast_time=None))
            if request.path == "/api/recommendations":
                lat = number(param("lat", "4.7110"), "Latitud", -90, 90)
                lon = number(param("lon", "-74.0721"), "Longitud", -180, 180)
                try:
                    result = forecast(lat, lon)
                except (OSError, ValueError, KeyError, IndexError, TypeError):
                    return self.reply(503, {"error": "No fue posible validar el pronóstico. Intenta de nuevo o usa la demostración.", "activities": [], "outdoor_blocked": True, "safety_alert": {"code": "WEATHER_UNAVAILABLE", "message": "Pronóstico no disponible. No se generan recomendaciones."}})
                return self.reply(200, result)
        except ValueError as exc:
            return self.reply(400, {"error": str(exc)})
        return self.reply(404, {"error": "Ruta no encontrada"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Turismo y clima disponible en http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
