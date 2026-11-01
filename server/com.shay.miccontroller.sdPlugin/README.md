# Mic Controller Server Module

`micController.py` is the server-side entry point for the
`com.shay.miccontroller` Stream Deck plugin.

The module is registered automatically by `server/server.py`.

## Endpoint

- `GET /miccontroller/health`
- `GET /miccontroller/status`
- `GET /miccontroller/mute`
- `GET /miccontroller/unmute`
- `GET /miccontroller/toggle`
- `GET /miccontroller/events` (SSE)

The status endpoints return the latest Windows Endpoint and HID state:

```json
{
  "device": "HyperX SoloCast",
  "vid": 1008,
  "pid": 1931,
  "connected": true,
  "muted": false,
  "report_hex": "66 81 00 00 ...",
  "updated_at": "2026-10-30T00:00:00Z",
  "last_error": null
}
```

`/toggle` returns the actual Windows Endpoint mute state:

```json
{"status":"ok","ok":true,"muted":true}
```

`toggle`, `mute`, and `unmute` change the Windows capture Endpoint.
They do not write HID reports to the device.

## Standalone SoloCast HID reader

セットアップ済みのポータブルPythonを使って、SoloCastのHIDインターフェイスを列挙します。

```powershell
.runtime\python\python.exe server\com.shay.miccontroller.sdPlugin\soloCastHidReader.py --enumerate-only
```

Briefly probe every `MI_02` collection:

```powershell
.runtime\python\python.exe server\com.shay.miccontroller.sdPlugin\soloCastHidReader.py --probe --timeout-ms 300
```

Run the continuous reader:

```powershell
.runtime\python\python.exe server\com.shay.miccontroller.sdPlugin\soloCastHidReader.py
```
