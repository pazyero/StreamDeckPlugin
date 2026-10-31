"""HyperX SoloCast用のマイクミュート制御API。

SoloCastHidMonitorをバックグラウンド監視し、HTTP APIとSSEで現在状態を共有する。
"""

import importlib.util
import atexit
import json
from pathlib import Path
import sys

from flask import Blueprint, jsonify, Response

SERVER_ROOT = Path(__file__).resolve().parent.parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from common_logging import log_output


blueprint = Blueprint("micController", __name__)

# モジュールの同じディレクトリからHID監視処理を動的ロードする。
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
# プロセス終了時に監視スレッドとHIDデバイスを確実に停止する。
atexit.register(monitor.stop)


@blueprint.get("/miccontroller/health")
def health():
    """サーバーにマイク制御機能が登録されているかを確認する。"""
    return jsonify({"status": "ok"})


@blueprint.get("/miccontroller/status")
def get_status():
    """接続状態、ミュート状態、最終更新日時などのスナップショットを返す。"""
    return jsonify(monitor.snapshot())


@blueprint.get("/miccontroller/events")
def stream_status():
    """状態変更をServer-Sent Eventsとしてクライアントへ継続配信する。"""
    subscriber = monitor.subscribe_status()

    def event_stream():
        # 監視キューから状態通知を受け取り、未受信時はSSEのkeepaliveを送る。
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
    """Windows録音エンドポイントをミュート状態へ設定する。"""
    result = monitor.set_mute(True)
    status_code = 200 if result["ok"] else 404
    return jsonify(result), status_code


@blueprint.get("/miccontroller/unmute")
def unmute_microphone():
    """Windows録音エンドポイントのミュートを解除する。"""
    result = monitor.set_mute(False)
    status_code = 200 if result["ok"] else 404
    return jsonify(result), status_code


@blueprint.get("/miccontroller/toggle")
def toggle_microphone():
    """現在の録音エンドポイント状態を反転し、クライアント向け形式で返す。"""
    try:
        result = monitor.toggle_mute()
    except Exception as error:
        log_output("Toggle exception","error",logger_name="micController",exc_info=True,)
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
        log_output("Toggle response error","error",logger_name="micController",exc_info=True,)
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
    """BlueprintをFlaskへ登録し、HID監視スレッドを開始する。"""
    app.register_blueprint(blueprint)
    monitor.start()
