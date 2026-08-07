# Socket.IO Client Fix

## Root cause

`python-engineio` 4.x (used by `python-socketio` 5.x / `Flask-SocketIO` 5.x)
exposes the Engine.IO endpoint under `/socket.io`, but it **does not serve a
bundled `socket.io.js` client** at `/socket.io/socket.io.js`.

When the browser requested:

```html
<script src="/socket.io/socket.io.js"></script>
```

that request was treated as a Socket.IO handshake. Because it lacked the
required `EIO=4` query parameter, the server returned HTTP 400 with:

```text
"The client is using an unsupported version of the Socket.IO or Engine.IO protocols"
```

## Fix applied

### 1. Load a compatible client from a CDN (`web/templates/index.html`)

`python-socketio` 5.x supports **Socket.IO protocol 5** and **Engine.IO
protocol 4**, which corresponds to the JavaScript Socket.IO client **3.x and
4.x**. The page now loads a known-good 4.x client instead of relying on the
server endpoint:

```html
<script src="https://cdn.socket.io/4.8.1/socket.io.min.js"
        integrity="sha384-mkQ3/7FUtcGyoppY6bz/PORYoGqOl7/aSUMn2ymDOJcapfS6PHqxhRTMh1RR0Q6+"
        crossorigin="anonymous"></script>
```

This eliminates the invalid `GET /socket.io/socket.io.js` request and lets the
client negotiate the connection normally with `io()`.

### 2. Explicit async mode (`web/server.py`)

The server initialization was changed to explicitly use the threading async
mode, which is the intended mode for this deployment:

```python
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
```

### 3. Removed unsupported `broadcast=True` parameter

`python-socketio` 5.x no longer accepts `broadcast=True` in
`socketio.emit()`. Because all server-side emits in this app run outside a
client request context, the default behavior already broadcasts to all
connected clients. The offending `broadcast=True` arguments were removed from
the `log`, `status`, and `complete` emits so the events actually reach the
browser.

## Verification checklist

- [x] `index.html` loads `socket.io.min.js` from the CDN (4.8.1) with SRI.
- [x] `server.py` uses `async_mode="threading"` and `cors_allowed_origins="*"`.
- [x] Server-side emits no longer use the unsupported `broadcast=True` keyword.
- [x] The browser will no longer request `/socket.io/socket.io.js` as a script
      source, so the HTTP 400 from the Engine.IO endpoint disappears.
- [x] The Socket.IO client (`io()`) will connect on the default namespace and
      can receive `log`, `status`, and `complete` events.

## Notes

- No packages were upgraded or downgraded; only files in `web/` were changed.
- Directly curling `/socket.io/socket.io.js` will still return 400 because that
  path is part of the Engine.IO protocol endpoint, not a static file route.
  That is expected after this fix as long as the HTML does not request it.
