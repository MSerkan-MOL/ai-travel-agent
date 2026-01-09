import os
import requests
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")

def get_weather_type(description):
    desc_lower = description.lower()
    if "rain" in desc_lower or "drizzle" in desc_lower or "shower" in desc_lower or "yağmur" in desc_lower:
        return "rainy"
    elif "snow" in desc_lower or "kar" in desc_lower:
        return "snowy"
    elif "cloud" in desc_lower or "bulut" in desc_lower or "kapalı" in desc_lower:
        return "cloudy"
    elif "thunder" in desc_lower or "storm" in desc_lower or "fırtına" in desc_lower:
        return "stormy"
    elif "clear" in desc_lower or "açık" in desc_lower:
        return "sunny"
    elif "mist" in desc_lower or "fog" in desc_lower or "sis" in desc_lower:
        return "foggy"
    else:
        return "default"

def get_turkish_day_name(weekday):
    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    return days[weekday]

def get_weather(city, days=1):
    days = max(1, min(5, days))
    
    if days == 1:
        api_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=tr"
        
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            
            description = data["weather"][0]["description"]
            
            weather_info = {
                "city": data["name"],
                "type": "current",
                "forecasts": [{
                    "date": datetime.now().strftime("%d %B %Y"),
                    "day_name": get_turkish_day_name(datetime.now().weekday()),
                    "temperature": round(data["main"]["temp"]),
                    "description": description.capitalize(),
                    "weather_type": get_weather_type(description),
                    "feels_like": round(data["main"]["feels_like"]),
                    "humidity": data["main"]["humidity"],
                    "icon": data["weather"][0]["icon"]
                }]
            }
            return weather_info
        except requests.exceptions.RequestException as e:
            return {"error": f"Hava durumu bilgisi alınamadı: {str(e)}"}
        except KeyError:
            return {"error": "Hava durumu verisi işlenemedi"}
    else:
        api_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=tr"
        
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            
            daily_forecasts = {}
            for item in data["list"]:
                dt = datetime.fromtimestamp(item["dt"])
                date_str = dt.strftime("%Y-%m-%d")
                
                if date_str not in daily_forecasts:
                    hour = dt.hour
                    if 11 <= hour <= 14:
                        description = item["weather"][0]["description"]
                        daily_forecasts[date_str] = {
                            "date": dt.strftime("%d %B"),
                            "day_name": get_turkish_day_name(dt.weekday()),
                            "temperature": round(item["main"]["temp"]),
                            "description": description.capitalize(),
                            "weather_type": get_weather_type(description),
                            "feels_like": round(item["main"]["feels_like"]),
                            "humidity": item["main"]["humidity"],
                            "icon": item["weather"][0]["icon"]
                        }
            
            forecasts = list(daily_forecasts.values())[:days]
            
            weather_info = {
                "city": data["city"]["name"],
                "type": "forecast",
                "days": days,
                "forecasts": forecasts
            }
            return weather_info
        except requests.exceptions.RequestException as e:
            return {"error": f"Hava durumu bilgisi alınamadı: {str(e)}"}
        except KeyError as e:
            return {"error": f"Hava durumu verisi işlenemedi: {str(e)}"}

def search_hotels(location, budget=None, star_rating=None):
    import datetime
    api_url = "https://serpapi.com/search.json"
    
    today = datetime.date.today()
    check_in = today + datetime.timedelta(days=30)
    check_out = check_in + datetime.timedelta(days=1)
    
    params = {
        "engine": "google_hotels",
        "q": location,
        "check_in_date": check_in.strftime("%Y-%m-%d"),
        "check_out_date": check_out.strftime("%Y-%m-%d"),
        "adults": "2",
        "currency": "TRY",
        "gl": "tr",
        "hl": "tr",
        "api_key": SERP_API_KEY
    }
    
    if budget:
        params["max_price"] = budget
    
    if star_rating and star_rating in [2, 3, 4, 5]:
        params["hotel_class"] = star_rating
    
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        properties = data.get("properties", [])
        hotels = []
        
        for prop in properties[:5]:
            hotel_info = {
                "name": prop.get("name"),
                "type": prop.get("type"),
                "overall_rating": prop.get("overall_rating"),
                "reviews": prop.get("reviews"),
                "hotel_class": prop.get("hotel_class"),
                "description": prop.get("description"),
            }
            
            images = prop.get("images", [])
            if not images:
                if prop.get("thumbnail"):
                    hotel_info["image"] = prop.get("thumbnail")
            elif len(images) > 0:
                first_image = images[0]
                hotel_info["image"] = first_image.get("thumbnail") or first_image.get("original_image") or first_image.get("link")
            
            if "gps_coordinates" in prop:
                gps = prop["gps_coordinates"]
                hotel_info["latitude"] = gps.get("latitude")
                hotel_info["longitude"] = gps.get("longitude")
            
            if "rate_per_night" in prop:
                hotel_info["rate_per_night"] = prop["rate_per_night"].get("lowest")
            elif "total_rate" in prop:
                hotel_info["total_rate"] = prop["total_rate"].get("lowest")
            
            if "amenities" in prop:
                hotel_info["amenities"] = prop["amenities"][:5]
            
            hotels.append(hotel_info)
        
        currency_code = data.get("currency", "TRY")
        currency_symbol = data.get("currency_symbol", "₺")
        
        return {
            "location": location,
            "budget": budget,
            "star_rating": star_rating,
            "currency": currency_code,
            "currency_symbol": currency_symbol,
            "hotels": hotels
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Otel arama başarısız: {str(e)}"}
    except (KeyError, ValueError) as e:
        return {"error": f"Otel verisi işlenemedi: {str(e)}"}

def search_flights(departure, arrival, outbound_date, return_date=None, adults=1):
    api_url = "https://serpapi.com/search.json"
    
    params = {
        "engine": "google_flights",
        "departure_id": departure.upper(),
        "arrival_id": arrival.upper(),
        "outbound_date": outbound_date,
        "adults": str(adults),
        "currency": "TRY",
        "hl": "tr",
        "gl": "tr",
        "api_key": SERP_API_KEY
    }
    
    if return_date:
        params["return_date"] = return_date
        params["type"] = "1"
    else:
        params["type"] = "2"
    
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        best_flights = data.get("best_flights", [])
        other_flights = data.get("other_flights", [])
        all_flights = best_flights + other_flights
        
        flights = []
        for flight_option in all_flights[:5]:
            segments = flight_option.get("flights", [])
            
            flight_info = {
                "price": flight_option.get("price"),
                "type": flight_option.get("type"),
                "airline_logo": flight_option.get("airline_logo"),
                "total_duration": flight_option.get("total_duration"),
                "carbon_emissions": flight_option.get("carbon_emissions", {}).get("this_flight"),
                "booking_url": None,
                "flights": []
            }
            
            for segment in segments:
                segment_info = {
                    "departure_airport": segment.get("departure_airport", {}).get("name"),
                    "departure_code": segment.get("departure_airport", {}).get("id"),
                    "departure_time": segment.get("departure_airport", {}).get("time"),
                    "arrival_airport": segment.get("arrival_airport", {}).get("name"),
                    "arrival_code": segment.get("arrival_airport", {}).get("id"),
                    "arrival_time": segment.get("arrival_airport", {}).get("time"),
                    "duration": segment.get("duration"),
                    "airplane": segment.get("airplane"),
                    "airline": segment.get("airline"),
                    "airline_logo": segment.get("airline_logo"),
                    "flight_number": segment.get("flight_number"),
                    "travel_class": segment.get("travel_class"),
                    "legroom": segment.get("legroom"),
                }
                flight_info["flights"].append(segment_info)
            
            flights.append(flight_info)
        
        google_flights_url = f"https://www.google.com/travel/flights?q={departure.upper()}%20to%20{arrival.upper()}%20{outbound_date}"
        
        return {
            "departure": departure.upper(),
            "arrival": arrival.upper(),
            "outbound_date": outbound_date,
            "return_date": return_date,
            "adults": adults,
            "currency": "TRY",
            "currency_symbol": "₺",
            "google_flights_url": google_flights_url,
            "flights": flights
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Uçuş arama başarısız: {str(e)}"}
    except (KeyError, ValueError) as e:
        return {"error": f"Uçuş verisi işlenemedi: {str(e)}"}