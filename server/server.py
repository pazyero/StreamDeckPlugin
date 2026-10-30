import logging
import importlib.util
import sys
import traceback
from pathlib import Path

from flask import Flask, jsonify


SERVER_ROOT = Path(__file__).resolve().parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


# Add another feature module here. Each module must provide register(app).
MODULES = (
    SERVER_ROOT
    / "com.shay.dialaudiomixer.sdPlugin"
    / "dialAudioMixer.py",
    SERVER_ROOT
    / "com.shay.miccontroller.sdPlugin"
    / "micController.py",
)


def create_app():
    app = Flask(__name__)

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.logger.disabled = True

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        print("[Server] Unexpected exception:")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "ok": False,
            "message": f"Server error: {error}",
        }), 500

    for module_name in MODULES:
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
