"""Bound bodies before JSON parsing/auth, including chunked requests."""

from starlette.responses import JSONResponse


class RequestBodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # 1 MiB accommodates all three 20k-character notes even as escaped JSON.
        # Count actual bytes, not attacker-controlled Content-Length headers.
        limit = 8192 if scope["path"].rstrip("/") == "/api/auth/login" else 1048576
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > limit:
                response = JSONResponse(
                    {"detail": "Request too large"},
                    status_code=413,
                    headers={"Cache-Control": "no-store"},
                )
                return await response(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {
                    "type": "http.request",
                    "body": b"".join(chunks),
                    "more_body": False,
                }
            return await receive()

        await self.app(scope, replay, send)
