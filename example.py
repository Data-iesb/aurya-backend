"""
Exemplo de uso da API Aurya FUNASA
===================================
Consulta dados do SUS via WebSocket.

Uso:
    python3 example.py "Qual o gasto do SUS por região em 2025?"
"""

import asyncio
import json
import sys
import websockets

API_KEY = ""  # Solicite a chave de acesso
BASE_URL = "wss://api.dataiesb.com/aurya"


async def ask(question: str):
    url = f"{BASE_URL}/ws/example-session?api_key={API_KEY}"
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"input_string": question}))
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))

        print(resp["answer"])
        if resp.get("query"):
            print(f"\nSQL: {resp['query']}")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Qual o gasto total do SUS por região em 2025?"
    asyncio.run(ask(question))
