import importlib.util
import atexit
import json
import traceback
from pathlib import Path

from flask import Blueprint, jsonify, Response


blueprint = Blueprint("micController", __name__)

MODULE_DIR = Path(__file__).resolve().parent
MODULE_PATH = MODULE_DIR / "soloCastHidReader.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "soloCastHidReader",
    MODULE_PATH,
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"cannot load module: {MODULE_PATH}")

SOLO_CAST_READER = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(SOLO_CAST_READER)

monitor = SOLO_CAST_READER.SoloCastHidMonitor()
atexit.register(monitor.stop)


@blueprint.get("/miccontroller/health")
def health():
    return jsonify({"status": "ok"})


@blueprint.get("/miccontroller/status")
def get_status():
    return jsonify(monitor.snapshot())


@blueprint.get("/miccontroller/events")
def stream_status():
    subscriber = monitor.subscribe_status()

    def event_stream():
        try:
            while True:
                try:
                    status = subscriber.get(timeout=15)
                    yield "data: " + json.dumps(status) + "\n\n"
                except Exception:
                    yield ": keepalive\n\n"
        finally:
            monitor.unsubscribe_status(subscriber)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@blueprint.get("/miccontroller/mute")
def mute_microphone():
    result = monitor.set_mute(True)
    status_code = 200 if result["ok"] else 404
    return jsonify(result), status_code


@blueprint.get("/miccontroller/unmute")
def unmute_microphone():
    result = monitor.set_mute(False)
    status_code = 200 if result["ok"] else 404
    return jsonify(result), status_code


@blueprint.get("/miccontroller/toggle")
def toggle_microphone():
    try:
        result = monitor.toggle_mute()
    except Exception as error:
        print("[Mic Controller] Toggle exception:")
        traceback.print_exc()
        result = {
            "status": "error",
            "ok": False,
            "muted": None,
            "message": f"Toggle failed: {error}",
        }
    try:
        status_code = 200
        public_result = {
            "status": "ok" if result["ok"] else "error",
            "ok": bool(result["ok"]),
            "muted": (
                bool(result["muted"])
                if result["muted"] is not None
                else None
            ),
        }
        return Response(
            json.dumps(public_result, ensure_ascii=False),
            status=status_code,
            mimetype="application/json",
        )
    except Exception as error:
        traceback.print_exc()
        return Response(
            json.dumps(
                {
                    "status": "error",
                    "ok": False,
                    "muted": None,
                    "message": f"Failed to build toggle response: {error}",
                },
                ensure_ascii=False,
            ),
            status=500,
            mimetype="application/json",
        )


def register(app):
    app.register_blueprint(blueprint)
    monitor.start()
