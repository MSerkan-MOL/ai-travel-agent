from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from dotenv import load_dotenv
from typing import Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
import requests
from tool import get_weather, search_hotels, search_flights

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")

app = FastAPI()

# CORS middleware ekle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend klasörünü servis et
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# LangGraph Setup - Groq API
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    api_key=GROQ_API_KEY
)



class State(TypedDict):
    messages: Annotated[list, add_messages]






# Tool tanımlaması
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Belirtilen şehir için güncel hava durumu bilgisini getirir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Hava durumu sorgulanacak şehir adı"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "Belirtilen konumda bütçe ve yıldız sayısına göre otel arar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Otel aranacak konum veya şehir adı (örn: 'Bali', 'Istanbul', 'Paris')"
                    },
                    "budget": {
                        "type": "integer",
                        "description": "Maksimum gecelik fiyat (USD cinsinden, opsiyonel)"
                    },
                    "star_rating": {
                        "type": "integer",
                        "description": "Otel yıldız sayısı (2, 3, 4, veya 5, opsiyonel)"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Belirtilen kalkış ve varış noktaları arasında uçuş arar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "departure": {
                        "type": "string",
                        "description": "Kalkış havalimanı kodu (örn: 'IST', 'SAW', 'ESB', 'ADB')"
                    },
                    "arrival": {
                        "type": "string",
                        "description": "Varış havalimanı kodu (örn: 'CDG', 'JFK', 'LHR', 'AMS')"
                    },
                    "outbound_date": {
                        "type": "string",
                        "description": "Gidiş tarihi (YYYY-MM-DD formatında, örn: '2024-01-15')"
                    },
                    "return_date": {
                        "type": "string",
                        "description": "Dönüş tarihi (opsiyonel, YYYY-MM-DD formatında)"
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Yetişkin yolcu sayısı (varsayılan: 1)"
                    }
                },
                "required": ["departure", "arrival", "outbound_date"]
            }
        }
    }
]

llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State) -> State:
    messages = state["messages"]
    
    # Sistem promptu - TOOL KULLANIMI ÖNCELİKLİ!
    system_prompt = """Sen "TravelAI" adında profesyonel bir seyahat asistanısın.
 KRİTİK KURALLAR (MUTLAKA TAKİP ET):
1. HAVA DURUMU: Kullanıcı bir şehir için hava durumu sorarsa veya seyahat planında hava bilgisi isterse → MUTLAKA get_weather() tool'unu kullan.
2. OTEL ÖNERİSİ: Kullanıcı otel ararsa, konaklama sorarsa veya seyahat planında otel önerisi isterse → MUTLAKA search_hotels() tool'unu kullan.
3. UÇUŞ ARAMA: Kullanıcı uçuş, uçak bileti, flight ararsa → MUTLAKA search_flights() tool'unu kullan.
   - Havalimanı kodlarını biliyorsan kullan (IST=İstanbul, SAW=Sabiha Gökçen, ESB=Ankara, ADB=İzmir, CDG=Paris, JFK=New York, LHR=Londra)
   - Tarih YYYY-MM-DD formatında olmalı
4. SEYAHAT PLANI İSTENDİĞİNDE:
   Kullanıcı "plan hazırla", "gezi planı", "ne yapabilirim" gibi ifadeler kullanırsa:
   → İLK ÖNCE get_weather() çağır
   → SONRA search_hotels() çağır
   → Uçuş istenirse search_flights() çağır
   → TÜM TOOL sonuçları geldikten SONRA planı oluştur
5. ASLA uydurma hava/otel/uçuş bilgisi verme - her zaman tool'ları kullan!
GÖREV & KİŞİLİK:
- Sıcak, dostane, yardımsever
- Türkçe konuş, emoji kullan (abartmadan)
- Kullanıcı tarih belirtmemişse sor (uçuş için tarih ZORUNLU)
- Kültürel bilgin zengin, pratik önerilerde bulun"""
    
    # Sistem promptunu mesajların başına ekle (SystemMessage kullanarak)
    messages_with_system = [
        SystemMessage(content=system_prompt)
    ] + messages
    
    response = llm_with_tools.invoke(messages_with_system)
    return {"messages": [response]}

def tool_node(state: State) -> State:
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_results = []
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "get_weather":
                city = tool_call["args"]["city"]
                weather_data = get_weather(city)
                
                if "error" in weather_data:
                    result = weather_data["error"]
                else:
                    result = json.dumps(weather_data)
                
                tool_results.append(
                    ToolMessage(
                        content=result,
                        tool_call_id=tool_call["id"]
                    )
                )
            elif tool_call["name"] == "search_hotels":
                location = tool_call["args"]["location"]
                budget = tool_call["args"].get("budget")
                star_rating = tool_call["args"].get("star_rating")
                
                hotel_data = search_hotels(location, budget, star_rating)
                
                if "error" in hotel_data:
                    result = hotel_data["error"]
                else:
                    result = json.dumps(hotel_data)
                
                tool_results.append(
                    ToolMessage(
                        content=result,
                        tool_call_id=tool_call["id"]
                    )
                )
            elif tool_call["name"] == "search_flights":
                departure = tool_call["args"]["departure"]
                arrival = tool_call["args"]["arrival"]
                outbound_date = tool_call["args"]["outbound_date"]
                return_date = tool_call["args"].get("return_date")
                adults = tool_call["args"].get("adults", 1)
                
                flight_data = search_flights(departure, arrival, outbound_date, return_date, adults)
                
                if "error" in flight_data:
                    result = flight_data["error"]
                else:
                    result = json.dumps(flight_data)
                
                tool_results.append(
                    ToolMessage(
                        content=result,
                        tool_call_id=tool_call["id"]
                    )
                )
    
    return {"messages": tool_results}

def should_continue(state: State) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return "end"

# Graph oluştur
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges(
    "chatbot",
    should_continue,
    {
        "tools": "tools",
        "end": END
    }
)
graph_builder.add_edge("tools", "chatbot")

# Memory aktif - Her kullanıcı için konuşma geçmişi saklanır
memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

# Ana sayfa
@app.get("/")
async def get():
    with open("frontend/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    thread_id = f"user_{id(websocket)}"
    print(f"WebSocket connection established for thread: {thread_id}")
    
    try:
        while True:
            
            data = await websocket.receive_text()
            print(f"Received message: {data}")
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message:
                continue
            
            print(f"Processing message: {user_message}")
            
            # LangGraph ile işle - Memory AÇIK!
            try:
                state = {"messages": [HumanMessage(content=user_message)]}
                config = {"configurable": {"thread_id": thread_id}}
                
                print(f"Invoking graph with thread_id: {thread_id}")
                final_state = graph.invoke(state, config=config)
                print(f"Graph completed successfully")
            
                # Son AI mesajını ve tool verilerini bul
                messages = final_state["messages"]
                last_ai_message = None
                weather_data = None
                hotel_data = None
                flight_data = None
                
                # DEBUG: Tüm mesajları logla
                print(f"\n📋 Total messages in state: {len(messages)}")
                for i, msg in enumerate(messages):
                    msg_type = type(msg).__name__
                    if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls'):
                        print(f"  [{i}] {msg_type} - Tool calls: {len(msg.tool_calls) if msg.tool_calls else 0}")
                        if msg.tool_calls:
                            for tc in msg.tool_calls:
                                print(f"      → {tc['name']}({tc['args']})")
                    elif isinstance(msg, ToolMessage):
                        content_preview = msg.content[:100] if len(msg.content) > 100 else msg.content
                        print(f"  [{i}] {msg_type} - {content_preview}...")
                    else:
                        print(f"  [{i}] {msg_type}")
                
                # Son HumanMessage'ın index'ini bul
                last_human_index = -1
                for i, msg in enumerate(messages):
                    if isinstance(msg, HumanMessage):
                        last_human_index = i
                
                # Son AI mesajını bul (tool call olmayan)
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage) and not last_ai_message:
                        if not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                            last_ai_message = msg
                            break
                
                # Son HumanMessage'dan SONRA gelen TÜM ToolMessage'ları al
                if last_human_index >= 0:
                    recent_messages = messages[last_human_index + 1:]
                    
                    print(f"\n🔍 Processing {len(recent_messages)} messages after last HumanMessage")
                    
                    for msg in recent_messages:
                        if isinstance(msg, ToolMessage):
                            try:
                                parsed_data = json.loads(msg.content)
                                if "hotels" in parsed_data and not hotel_data:
                                    hotel_data = parsed_data
                                    print("✅ Found hotel data")
                                elif "temperature" in parsed_data and not weather_data:
                                    weather_data = parsed_data
                                    print("✅ Found weather data")
                                elif "flights" in parsed_data and not flight_data:
                                    flight_data = parsed_data
                                    print("✅ Found flight data")
                            except Exception as e:
                                print(f"❌ Error parsing tool message: {e}")
                                pass

            
                # Yanıtı gönder
                if hotel_data and "error" not in hotel_data:
                    print(f"Sending hotel data: {json.dumps(hotel_data, indent=2)}")
                    await websocket.send_text(json.dumps({
                        "type": "hotels",
                        "data": hotel_data
                    }))
                
                if weather_data and "error" not in weather_data:
                    print(f"Sending weather data")
                    await websocket.send_text(json.dumps({
                        "type": "weather",
                        "data": weather_data
                    }))
                
                if flight_data and "error" not in flight_data:
                    print(f"Sending flight data")
                    await websocket.send_text(json.dumps({
                        "type": "flights",
                        "data": flight_data
                    }))
                
                # Eğer hiç tool sonucu yoksa AI mesajı gönder
                if not hotel_data and not weather_data and not flight_data and last_ai_message and last_ai_message.content:
                    print(f"Sending AI message: {last_ai_message.content}")
                    await websocket.send_text(json.dumps({
                        "type": "message",
                        "content": last_ai_message.content
                    }))
                
            except Exception as inner_e:
                print(f"Error processing message: {inner_e}")
                import traceback
                traceback.print_exc()
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": f"Bir hata oluştu: {str(inner_e)}"
                }))
            
    except WebSocketDisconnect:
        print(f"Client disconnected: {thread_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": "Bir hata oluştu. Lütfen tekrar deneyin."
            }))
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,  port=8002)