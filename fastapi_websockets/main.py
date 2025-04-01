from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import logging
import asyncio
from connect4 import PLAYER1, PLAYER2, Connect4
import itertools
import json
import secrets

app = FastAPI()

JOIN = {}

WATCH = {}

ACTIVE_CONNECTIONS: list[WebSocket] = []

@app.get("/")
def hello():
  return "Hello"

async def error(websocket, message):
    event = {
        "type": "error",
        "message": message,
    }
    await websocket.send_json(event)

async def replay(websocket, game):
    # Make a copy to avoid an exception if game.moves changes while iteration
    # is in progress. If a move is played while replay is running, moves will
    # be sent out of order but each move will be sent once and eventually the
    # UI will be consistent.
    for player, column, row in game.moves.copy():
        event = {
            "type": "play",
            "player": player,
            "column": column,
            "row": row,
        }
        await websocket.send_json(event)


async def play(websocket, game, player, connected):
    """
    Receive and process moves from a player.
    """
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
            await error(websocket, str(exc))
            continue

        # Send a "play" event to update the UI.
        event = {
            "type": "play",
            "player": player,
            "column": column,
            "row": row,
        }
        for connection in connected:
          try:
              await connection.send_json(event)
          except WebSocketDisconnect:
              # Handle disconnects and remove the client from the list
              connected.remove(connection)
              logging.info("A client disconnected.")

        if game.winner is not None:
            event = {
                "type": "win",
                "player": game.winner,
            }
          
            for connection in connected:
              try:
                  await connection.send_json(event)
              except WebSocketDisconnect:
                connected.remove(connection)
                logging.info("A client disconnected.")

    except WebSocketDisconnect:
      logging.info("Client disconnected")


async def start(websocket):
    # Initialize a Connect Four game, the set of WebSocket connections
    # receiving moves from this game, and secret access token.    game = Connect4()
    game = Connect4()
    connected = {websocket}
    ACTIVE_CONNECTIONS.append(websocket)

    join_key = secrets.token_urlsafe(12)
    JOIN[join_key] = game, connected
    print(JOIN)
    watch_key = secrets.token_urlsafe(12)
    WATCH[watch_key] = game, connected
    print(WATCH)
    try:
        # Send the secret access tokens to the browser of the first player,
        # where they'll be used for building "join" and "watch" links.
        event = {
            "type": "init",
            "join": join_key,
            "watch": watch_key,
        }
        await websocket.send_json(event)
        # Receive and process moves from the first player.
        await play(websocket, game, PLAYER1, connected)
        while True:
            message = await websocket.receive_text()  
    except WebSocketDisconnect:
      logging.info("Client disconnected")

    finally:
      del JOIN[join_key]
      del WATCH[watch_key]


async def join(websocket, join_key):
    """
    Handle a connection from the second player: join an existing game.
    """
    try:
        game, connected = JOIN[join_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    # Register to receive moves from this game.
    ACTIVE_CONNECTIONS.append(websocket)
    connected.add(websocket)
    try:
        # Send the first move, in case the first player already played it.
        await replay(websocket, game)
        # Receive and process moves from the second player.
        await play(websocket, game, PLAYER2, connected)
    finally:
        ACTIVE_CONNECTIONS.remove(websocket)
        connected.remove(websocket)

async def watch(websocket, watch_key):
    """
    Handle a connection from a spectator: watch an existing game.
    """
    # Find the Connect Four game.
    try:
        game, connected = WATCH[watch_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    # Register to receive moves from this game.
    connected.add(websocket)
    ACTIVE_CONNECTIONS.append(websocket)
    try:
        # Send previous moves, in case the game already started.
        await replay(websocket, game)
        # Keep the connection open, but don't receive any messages.
        await websocket.wait_closed()
    finally:
        ACTIVE_CONNECTIONS.remove(websocket)
        connected.remove(websocket)



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
      while True:
        message = await websocket.receive_text()
        event = json.loads(message)

        if "join" in event:
            # Second player joins an existing game.
            await join(websocket, event["join"])
        elif "watch" in event:
            # Spectator watches an existing game.
            await watch(websocket, event["watch"])
        else:
            # First player starts a new game.
            await start(websocket)
    except WebSocketDisconnect:
      logging.info("Client disconnected")

if __name__ == "__main__":
  uvicorn.run("main:app", port=5000, log_level="info")