
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json

app = FastAPI()


@app.get("/")
async def get():
    with open("index.html") as f:
        return HTMLResponse(content=f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    while True:
       
        data = await websocket.receive_text()
        
       
        state = {"messages": [HumanMessage(content=data)]}
        config = {"configurable": {"thread_id": "user_1"}}
        final_state = graph.invoke(state, config)
        
        
        response = final_state["messages"][-1].content
        await websocket.send_text(json.dumps({
            "type": "message",
            "content": response
        }))