# 共通ログ出力処理。

import inspect
import logging
import os
from typing import Literal, Optional, Union


LogLevel = Literal["debug", "info", "warning", "error", "critical"]
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
LOGGING_LEVEL = logging.INFO

def set_logging_level(level: int = logging.INFO) -> None:
# アプリケーション共通のログ形式とレベルを設定する。
    global LOGGING_LEVEL
    if isinstance(level, str):
        LOGGING_LEVEL = LOG_LEVELS.get(level.strip().upper(), logging.INFO)
    elif isinstance(level, int):
        LOGGING_LEVEL = level
    logging.getLogger().setLevel(LOGGING_LEVEL)

def configure_logging() -> None:
# アプリケーション共通のログ形式とレベルを設定する。
        logging.basicConfig(
            level=LOGGING_LEVEL,
            format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
        )


def infer_logger_name() -> str:
    for frame_info in inspect.stack()[2:]:
        filename = os.path.abspath(frame_info.filename)
        if filename != os.path.abspath(__file__):
            return os.path.splitext(os.path.basename(filename))[0]
    return "StreamDeckPlugin"


def debug_log(message: object = "", *, logger_name: str = None, exc_info: bool = False) -> None:
# すべての文言出力をloggingへ送る共通関数。
    configure_logging()
    logger = logging.getLogger(logger_name if logger_name is not None else infer_logger_name())
    getattr(logger, "debug")(str(message), exc_info=exc_info)


def info_log(message: object = "", *, logger_name: str = None, exc_info: bool = False) -> None:
# すべての文言出力をloggingへ送る共通関数。
    configure_logging()
    logger = logging.getLogger(logger_name if logger_name is not None else infer_logger_name())
    getattr(logger, "info")(str(message), exc_info=exc_info)


def warning_log(message: object = "", *, logger_name: str = None, exc_info: bool = False) -> None:
# すべての文言出力をloggingへ送る共通関数。
    configure_logging()
    logger = logging.getLogger(logger_name if logger_name is not None else infer_logger_name())
    getattr(logger, "warning")(str(message), exc_info=exc_info)


def error_log(message: object = "", *, logger_name: str = None, exc_info: bool = True) -> None:
# すべての文言出力をloggingへ送る共通関数。
    configure_logging()
    logger = logging.getLogger(logger_name if logger_name is not None else infer_logger_name())
    getattr(logger, "error")(str(message), exc_info=exc_info)


def critical_log(message: object = "", *, logger_name: str = None, exc_info: bool = True) -> None:
# すべての文言出力をloggingへ送る共通関数。
    configure_logging()
    logger = logging.getLogger(logger_name if logger_name is not None else infer_logger_name())
    getattr(logger, "critical")(str(message), exc_info=exc_info)

