import {createBoard, playMove} from "./style.js"


function initGame(websocket) {
  websocket.addEventListener("open", () => {
    // Send an "init" event according to who is connecting.
    const params = new URLSearchParams(window.location.search);
    let event = { type: "init" };
    if (params.has("join")) {
      // Second player joins an existing game.
      event.join = params.get("join");
    } else if (params.has("watch")) {
      // Spectator watches an existing game.
      event.watch = params.get("watch");
    } else {
      // First player starts a new game.
    }
    websocket.send(JSON.stringify(event));
  });
}


window.addEventListener("DOMContentLoaded", () => {
  const board = document.querySelector(".board")
  createBoard(board)
  const websocket = new WebSocket("ws://localhost:5000/ws")
  initGame(websocket)
  receiveMoves(board, websocket)
  sendMoves(board, websocket)
})

function sendMoves(board, websocket){
  const params = new URLSearchParams(window.location.search);
  if (params.has("watch")) {
    return;
  }
  board.addEventListener("click", ({target}) => {
    
    const column = target.dataset.column 
    if (column === undefined) {
      return;
    }
    const event = {
      type: "play",
      column: parseInt(column, 10),
    };
    websocket.send(JSON.stringify(event));
  })
}

function showMessage(message) {
  window.setTimeout(() => window.alert(message), 50);
}


function receiveMoves(board, websocket){
  websocket.addEventListener("message", ({data}) => {
    const event = JSON.parse(data)  
    switch (event.type) {
      case "init":
        // Create links for inviting the second player and spectators.
        document.querySelector(".join").href = "?join=" + event.join;
        document.querySelector(".watch").href = "?watch=" + event.watch;
        break;
      case "play":
        playMove(board, event.player, event.column, event.row);
        break;
      case "win":
        showMessage(`Player ${event.player} wins!`);
        websocket.close(1000);
        break;
      case "error":
        showMessage(event.message);
        break;
      default:
        throw new Error(`Unsupported event type: ${event.type}.`);
    }
  })
}