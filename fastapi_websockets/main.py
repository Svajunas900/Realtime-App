from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import logging
import asyncio
from connect4 import PLAYER1, PLAYER2, Connect4
import itertools
import json

app = FastAPI()

@app.get("/")
def hello():
  return "Hello"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    
    await websocket.accept()
    game = Connect4()
    turns = itertools.cycle([PLAYER1, PLAYER2])
    player = next(turns)
    try: 
      while True:
        message = await websocket.receive_text()
        try:
          event = json.loads(message)
          assert event["type"] == "play"
          column = event["column"]
          row = game.play(player, column)
        except ValueError as exc:
          # Send an "error" event if the move was illegal.
          event = {
              "type": "error",
              "message": str(exc),
          }
          await websocket.send_json(event)
        event = {
                "type": "play",
                "player": player,
                "column": column,
                "row": row,
            }
        await websocket.send_json(event)

        if game.winner is not None:
            event = {
                "type": "win",
                "player": game.winner,
            }
            await websocket.send_json(event)

        # Alternate turns.
        player = next(turns)
    except WebSocketDisconnect:
        logging.info("Client disconnected")

if __name__ == "__main__":
  uvicorn.run("main:app", port=5000, log_level="info")