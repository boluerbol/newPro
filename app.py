import json
import os
import urllib.parse
import urllib.request

from flask import Flask, render_template, request

app = Flask(__name__)

# Бесплатный API Open-Meteo, ключ не нужен
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Москва")

# Коды погоды WMO -> описание и иконка
WEATHER_CODES = {
    0: ("Ясно", "☀️"),
    1: ("Преимущественно ясно", "🌤️"),
    2: ("Переменная облачность", "⛅"),
    3: ("Пасмурно", "☁️"),
    45: ("Туман", "🌫️"),
    48: ("Изморозь", "🌫️"),
    51: ("Слабая морось", "🌦️"),
    53: ("Морось", "🌦️"),
    55: ("Сильная морось", "🌧️"),
    61: ("Небольшой дождь", "🌦️"),
    63: ("Дождь", "🌧️"),
    65: ("Сильный дождь", "🌧️"),
    66: ("Ледяной дождь", "🌧️"),
    67: ("Сильный ледяной дождь", "🌧️"),
    71: ("Небольшой снег", "🌨️"),
    73: ("Снег", "🌨️"),
    75: ("Сильный снег", "❄️"),
    77: ("Снежная крупа", "🌨️"),
    80: ("Ливень", "🌦️"),
    81: ("Сильный ливень", "🌧️"),
    82: ("Очень сильный ливень", "⛈️"),
    85: ("Снегопад", "🌨️"),
    86: ("Сильный снегопад", "❄️"),
    95: ("Гроза", "⛈️"),
    96: ("Гроза с градом", "⛈️"),
    99: ("Сильная гроза с градом", "⛈️"),
}

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def describe(code):
    return WEATHER_CODES.get(code, ("Неизвестно", "❔"))


def fetch_json(url, params):
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full_url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_city(name):
    data = fetch_json(GEO_URL, {"name": name, "count": 1, "language": "ru", "format": "json"})
    results = data.get("results")
    return results[0] if results else None


def get_weather(lat, lon):
    return fetch_json(WEATHER_URL, {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "wind_speed_10m,weather_code,pressure_msl",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "timezone": "auto",
        "wind_speed_unit": "ms",
        "forecast_days": 7,
    })


def build_forecast(daily):
    from datetime import date
    days = []
    for i, day in enumerate(daily["time"]):
        d = date.fromisoformat(day)
        text, icon = describe(daily["weather_code"][i])
        days.append({
            "label": "Сегодня" if i == 0 else f"{WEEKDAYS[d.weekday()]} {d.day:02d}.{d.month:02d}",
            "icon": icon,
            "text": text,
            "max": round(daily["temperature_2m_max"][i]),
            "min": round(daily["temperature_2m_min"][i]),
        })
    return days


@app.route("/")
def index():
    city_name = request.args.get("city", DEFAULT_CITY).strip() or DEFAULT_CITY
    error = None
    weather = None
    try:
        city = find_city(city_name)
        if not city:
            error = f"Город «{city_name}» не найден"
        else:
            data = get_weather(city["latitude"], city["longitude"])
            cur = data["current"]
            text, icon = describe(cur["weather_code"])
            weather = {
                "city": city["name"],
                "country": city.get("country", ""),
                "temp": round(cur["temperature_2m"]),
                "feels": round(cur["apparent_temperature"]),
                "humidity": cur["relative_humidity_2m"],
                "wind": cur["wind_speed_10m"],
                "pressure": round(cur["pressure_msl"] * 0.750062),  # гПа -> мм рт. ст.
                "text": text,
                "icon": icon,
                "forecast": build_forecast(data["daily"]),
            }
    except Exception as e:  # нет интернета, API недоступен и т.п.
        error = f"Не удалось получить погоду: {e}"
    return render_template("index.html", weather=weather, error=error, query=city_name)


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
