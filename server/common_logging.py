"""共通ログ出力処理。"""

import logging
from typing import Literal


LogLevel = Literal["debug", "info", "warning", "error", "critical"]


def configure_logging(level: int = logging.INFO) -> None:
    """アプリケーション共通のログ形式とレベルを設定する。"""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
        )


def log_output(
    message: object = "",
    level: LogLevel = "info",
    *,
    logger_name: str = "StreamDeckPlugin",
    exc_info: bool = False,
) -> None:
    """すべての文言出力をloggingへ送る共通関数。"""
    configure_logging()
    logger = logging.getLogger(logger_name)
    getattr(logger, level)(str(message), exc_info=exc_info)
