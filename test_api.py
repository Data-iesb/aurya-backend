#!/usr/bin/env python3
"""Test Aurya API endpoints + WebSocket with a real SUS question."""

import asyncio
import json
import httpx
import websockets

BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"
SESSION = "test-session-001"


def test_http():
    print("=" * 60)
    print("HTTP ENDPOINTS")
    print("=" * 60)

    with httpx.Client(base_url=BASE, timeout=10) as c:
        # Root
        r = c.get("/")
        print(f"\n✅ GET /  → {r.json()}")

        # Health
        r = c.get("/health")
        print(f"✅ GET /health  → {r.json()}")

        # Sessions
        r = c.get("/sessions")
        print(f"✅ GET /sessions  → {r.json()}")

        # Cache stats
        r = c.get("/cache-stats")
        print(f"✅ GET /cache-stats  → {r.json()}")


async def test_websocket():
    print("\n" + "=" * 60)
    print("WEBSOCKET — Real SUS question")
    print("=" * 60)

    uri = f"{WS_BASE}/ws/{SESSION}"
    print(f"\nConnecting to {uri}...")

    async with websockets.connect(uri) as ws:
        # Question 1: simple greeting
        q1 = {"input_string": "Olá", "message_id": "msg-1"}
        print(f"\n→ Sending: {q1['input_string']}")
        await ws.send(json.dumps(q1))
        r1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
        print(f"← Category: {r1.get('category')}")
        print(f"← Answer: {r1.get('answer', '')[:200]}")

        # Question 2: real data query
        q2 = {
            "input_string": "Qual o total de procedimentos do SUS por região em 2025?",
            "message_id": "msg-2",
        }
        print(f"\n→ Sending: {q2['input_string']}")
        await ws.send(json.dumps(q2))
        r2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
        print(f"← Category: {r2.get('category')}")
        print(f"← SQL: {r2.get('query')}")
        print(f"← Timing: {r2.get('timing')}")
        print(f"← Answer:\n{r2.get('answer', '')[:500]}")

    print(f"\n✅ WebSocket test complete")


if __name__ == "__main__":
    test_http()
    asyncio.run(test_websocket())
    print("\n🏁 All tests passed!")
