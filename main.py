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
from tool import get_weather, search_hotels, search_flights

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    api_key=GROQ_API_KEY
)

class State(TypedDict):
    messages: Annotated[list, add_messages]

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Belirtilen şehir için hava durumu bilgisini getirir. Anlık veya 5 güne kadar tahmin alınabilir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Hava durumu sorgulanacak şehir adı"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Kaç günlük tahmin isteniyor (1=anlık/bugün, 2-5=çok günlük tahmin). Varsayılan 1."
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
                        "description": "Otel aranacak konum veya şehir adı"
                    },
                    "budget": {
                        "type": "integer",
                        "description": "Maksimum gecelik fiyat (opsiyonel)"
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
                        "description": "Kalkış havalimanı kodu (örn: IST, SAW, ESB, ADB)"
                    },
                    "arrival": {
                        "type": "string",
                        "description": "Varış havalimanı kodu (örn: CDG, JFK, LHR, AMS)"
                    },
                    "outbound_date": {
                        "type": "string",
                        "description": "Gidiş tarihi (YYYY-MM-DD formatında)"
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

def chatbot(state: State):
    messages = state["messages"]
    
    system_prompt = """Sen "TravelAI" adında profesyonel bir seyahat asistanısın.
KRİTİK KURALLAR:
1. HAVA DURUMU: Kullanıcı hava durumu sorarsa → get_weather() kullan
2. OTEL: Kullanıcı otel ararsa → search_hotels() kullan
3. UÇUŞ: Kullanıcı uçuş ararsa → search_flights() kullan
4. ASLA uydurma bilgi verme - her zaman tool'ları kullan!
KİŞİLİK:
- Türkçe konuş, emoji kullan
- Tarih belirtilmemişse sor (uçuş için tarih ZORUNLU)"""
    
    messages_with_system = [SystemMessage(content=system_prompt)] + messages
    response = llm_with_tools.invoke(messages_with_system)
    return {"messages": [response]}

def tool_node(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    tool_results = []
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "get_weather":
                city = tool_call["args"]["city"]
                days = tool_call["args"].get("days", 1)
                weather_data = get_weather(city, days)
                
                if "error" in weather_data:
                    result = weather_data["error"]
                else:
                    result = json.dumps(weather_data)
                
                tool_results.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
                
            elif tool_call["name"] == "search_hotels":
                location = tool_call["args"]["location"]
                budget = tool_call["args"].get("budget")
                star_rating = tool_call["args"].get("star_rating")
                hotel_data = search_hotels(location, budget, star_rating)
                
                if "error" in hotel_data:
                    result = hotel_data["error"]
                else:
                    result = json.dumps(hotel_data)
                
                tool_results.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
                
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
                
                tool_results.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
    
    return {"messages": tool_results}

def should_continue(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return "end"

graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", should_continue, {"tools": "tools", "end": END})
graph_builder.add_edge("tools", "chatbot")

memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

@app.get("/")
async def get():
    with open("frontend/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    thread_id = f"user_{id(websocket)}"
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message:
                continue
            
            try:
                state = {"messages": [HumanMessage(content=user_message)]}
                config = {"configurable": {"thread_id": thread_id}}
                final_state = graph.invoke(state, config=config)
                
                messages = final_state["messages"]
                last_ai_message = None
                weather_data = None
                hotel_data = None
                flight_data = None
                
                last_human_index = -1
                for i, msg in enumerate(messages):
                    if isinstance(msg, HumanMessage):
                        last_human_index = i
                
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage) and not last_ai_message:
                        if not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                            last_ai_message = msg
                            break
                
                if last_human_index >= 0:
                    recent_messages = messages[last_human_index + 1:]
                    
                    for msg in recent_messages:
                        if isinstance(msg, ToolMessage):
                            try:
                                parsed_data = json.loads(msg.content)
                                if "hotels" in parsed_data and not hotel_data:
                                    hotel_data = parsed_data
                                elif "forecasts" in parsed_data and not weather_data:
                                    weather_data = parsed_data
                                elif "flights" in parsed_data and not flight_data:
                                    flight_data = parsed_data
                            except:
                                pass
                
                if hotel_data and "error" not in hotel_data:
                    await websocket.send_text(json.dumps({"type": "hotels", "data": hotel_data}))
                
                if weather_data and "error" not in weather_data:
                    await websocket.send_text(json.dumps({"type": "weather", "data": weather_data}))
                
                if flight_data and "error" not in flight_data:
                    await websocket.send_text(json.dumps({"type": "flights", "data": flight_data}))
                
                if not hotel_data and not weather_data and not flight_data and last_ai_message and last_ai_message.content:
                    await websocket.send_text(json.dumps({"type": "message", "content": last_ai_message.content}))
                
            except Exception as e:
                await websocket.send_text(json.dumps({"type": "error", "content": f"Bir hata oluştu: {str(e)}"}))
            
    except WebSocketDisconnect:
        pass
    except:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8002)