
import os
import requests
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")
def get_weather(city: str) -> dict:
    """Belirtilen şehir için hava durumu bilgisi getirir."""
    api_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        weather_info = {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "description": data["weather"][0]["description"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"]
        }
        return weather_info
    except requests.exceptions.RequestException as e:
        return {"error": f"Hava durumu bilgisi alınamadı: {str(e)}"}
    except KeyError:
        return {"error": "Hava durumu verisi işlenemedi"}



def search_hotels(location: str, budget: int = None, star_rating: int = None) -> dict:
    """Google Hotels API kullanarak otel arar."""
    import datetime
    api_url = "https://serpapi.com/search.json"
    
    # Varsayılan tarihler (bugün + 30 gün ve + 31 gün)
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
    
    print(f"🏨 Searching hotels with params: location={location}, budget={budget}, star_rating={star_rating}")
    print(f"🔍 API params: {params}")
    
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


def search_flights(departure: str, arrival: str, outbound_date: str, 
                   return_date: str = None, adults: int = 1) -> dict:
    """Google Flights API kullanarak uçuş arar.
    
    Args:
        departure: Kalkış havalimanı kodu (örn: IST, SAW, ESB)
        arrival: Varış havalimanı kodu (örn: CDG, JFK, LHR)
        outbound_date: Gidiş tarihi (YYYY-MM-DD formatında)
        return_date: Dönüş tarihi (opsiyonel, YYYY-MM-DD formatında)
        adults: Yetişkin yolcu sayısı
    """
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
    
    # Gidiş-dönüş ise return_date ekle
    if return_date:
        params["return_date"] = return_date
        params["type"] = "1"  # Round trip
    else:
        params["type"] = "2"  # One way
    
    print(f"✈️ Searching flights: {departure} → {arrival}, date: {outbound_date}")
    print(f"🔍 API params: {params}")
    
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Best flights ve other flights'ı al
        best_flights = data.get("best_flights", [])
        other_flights = data.get("other_flights", [])
        all_flights = best_flights + other_flights
        
        flights = []
        for flight_option in all_flights[:5]:  # En fazla 5 uçuş
            # İlk uçuş segmentinin bilgilerini al
            segments = flight_option.get("flights", [])
            first_segment = segments[0] if segments else {}
            
            # Google Flights'a yönlendiren URL oluştur
            # Format: IST-CDG şeklinde
            booking_url = f"https://www.google.com/travel/flights/search?tfs=CBwQAhopEgoyMDI1LTEyLTI5agwIAhIIL20vMDFwcWpyDAgCEggvbS8wNnpwcUABSAFwAYIBCwj___________8BmAEB&curr=TRY"
            
            flight_info = {
                "price": flight_option.get("price"),
                "type": flight_option.get("type"),
                "airline_logo": flight_option.get("airline_logo"),
                "total_duration": flight_option.get("total_duration"),
                "carbon_emissions": flight_option.get("carbon_emissions", {}).get("this_flight"),
                "booking_url": None,  # Her uçuş için ayrı URL yok
                "flights": []
            }
            
            # Her bir uçuş segmentini ekle
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
        
        # Google Flights arama URL'i oluştur
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