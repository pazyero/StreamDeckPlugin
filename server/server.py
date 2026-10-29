import importlib
import logging
import importlib.util
from pathlib import Path

from flask import Flask


# Add another feature module here. Each module must provide register(app).
MODULES = (
    Path(__file__).parent
    / "com.shay.dialaudiomixer.sdPlugin"
    / "dialAudioMixer.py",
)


def create_app():
    app = Flask(__name__)

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.logger.disabled = True

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
    app.run(port=8823)
