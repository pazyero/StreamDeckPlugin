# Stream Deckプラグイン向けローカルHTTPサーバー。
# 機能モジュール一覧でFlask Blueprintを動的に登録し、
# 127.0.0.1:8823で全機能への共通API窓口を提供する。

import logging
import importlib.util
import json
import sys
import traceback
from pathlib import Path

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


# サーバーディレクトリをPythonの検索パスへ追加し、機能モジュールを相対位置から読めるようにする。
SERVER_ROOT = Path(__file__).resolve().parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


# 機能モジュール一覧。各モジュールはregister(app)を提供する必要がある。
MODULES = (
    SERVER_ROOT
    / "com.shay.dialaudiomixer.sdPlugin"
    / "dialAudioMixer.py",
    SERVER_ROOT
    / "com.shay.miccontroller.sdPlugin"
    / "micController.py",
)

# setup.ps1がインストール対象をこのファイルへ保存し、
# インストールされていない機能モジュールはサーバーへ登録しない。
# 設定ファイルがない旧環境では、互換性のため両方を有効として扱う。
PLUGIN_CONFIG = SERVER_ROOT / "installed_plugins.json"
ENABLED_MODULES = {"dial": True, "mic": True}
if PLUGIN_CONFIG.exists():
    try:
        configured = json.loads(PLUGIN_CONFIG.read_text(encoding="utf-8"))
        if isinstance(configured, dict):
            for module_name in ("dial", "mic"):
                value = configured.get(module_name, True)
                ENABLED_MODULES[module_name] = value if isinstance(value, bool) else True
        else:
            print("[Server] plugin configuration must contain a JSON object; defaults are used.")
    except Exception as error:
        print(f"[Server] プラグイン設定を読み込めませんでした: {error}")

ACTIVE_MODULES = (
    MODULES[0] if ENABLED_MODULES["dial"] else None,
    MODULES[1] if ENABLED_MODULES["mic"] else None,
)


def create_app():
# Flaskアプリを生成し、共通例外処理と機能モジュールを登録する。
    app = Flask(__name__)

    @app.get("/health")
    def server_health():
        return jsonify({
            "status": "ok",
            "dial": ENABLED_MODULES["dial"],
            "mic": ENABLED_MODULES["mic"],
        })

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.logger.disabled = True

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
# 未処理例外をサーバーログへ記録し、クライアントへは内部情報を公開しない。
        if isinstance(error, HTTPException):
            return jsonify({
                "status": "error",
                "ok": False,
                "message": error.description,
            }), error.code
        print("[Server] Unexpected exception:")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "ok": False,
            "message": "Server error",
        }), 500

    for module_name in ACTIVE_MODULES:
        if module_name is None:
            continue
        # モジュールをファイル名から動的ロードし、提供されるregister関数でBlueprintを登録する。
        module_name = Path(module_name)
        module_id = module_name.stem
        spec = importlib.util.spec_from_file_location(module_id, module_name)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load module: {module_name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        register = getattr(module, "register", None)
        if not callable(register):
            raise RuntimeError(
                f"{module_name}.py must provide a register(app) function"
            )
        register(app)

    return app


app = create_app()


if __name__ == "__main__":
    try:
        app.run(
            host="127.0.0.1",
            port=8823,
            threaded=True,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
