"""HyperX SoloCastのHIDレポート監視とWindows録音エンドポイント制御。

HIDインターフェイスからミュートボタン状態を読み取り、pycaw経由でWindows側の
録音ミュート状態へ反映する。単体診断用CLIとしても利用できる。
"""

import argparse
import logging
import os
import time
import threading
import warnings
from queue import Queue
from typing import Iterable, Optional

import hid


VID = 0x03F0
PID = 0x078B
DEFAULT_READ_TIMEOUT_MS = 25
DEFAULT_RECONNECT_DELAY_SECONDS = 0.25


def parse_mute_state(report: Iterable[int], state_index: int = 2) -> Optional[bool]:
    """HIDレポートの指定バイトをミュート状態へ変換する。"""
    data = bytes(report)
    if len(data) <= state_index:
        return None

    if data[state_index] == 0x01:
        return True
    if data[state_index] == 0x00:
        return False
    return None


def format_hex(report: Iterable[int]) -> str:
    return bytes(report).hex(" ")


def enumerate_solo_cast_devices() -> list[dict]:
    """VID/PIDでSoloCastと一致するHIDデバイスだけを列挙する。"""
    devices = hid.enumerate(VID, PID)
    return [
        device
        for device in devices
        if device.get("vendor_id") == VID and device.get("product_id") == PID
    ]


def is_mi_02_path(device: dict) -> bool:
    path = device.get("path")
    if isinstance(path, bytes):
        path = os.fsdecode(path)
    return "mi_02" in str(path).lower()


def select_solo_cast_hid_device(devices: Iterable[dict]) -> Optional[dict]:
    """Vendor Usage Pageを持つMI_02インターフェイスを優先して選択する。"""
    candidates = list(devices)
    mi_02_candidates = [device for device in candidates if is_mi_02_path(device)]
    if mi_02_candidates:
        vendor_candidates = [
            device
            for device in mi_02_candidates
            if device.get("usage_page") == 65472
        ]
        if vendor_candidates:
            return vendor_candidates[0]
        return mi_02_candidates[0]
    return candidates[0] if candidates else None


def print_device(device: dict) -> None:
    for key in (
        "vendor_id",
        "product_id",
        "manufacturer_string",
        "product_string",
        "serial_number",
        "interface_number",
        "usage_page",
        "usage",
        "path",
    ):
        if key in device:
            value = device[key]
            if isinstance(value, bytes):
                value = os.fsdecode(value)
            print(f"{key}: {value}")
    print("mi_02: ", "yes" if is_mi_02_path(device) else "no")
    print()


def open_device(device: dict):
    path = device["path"]
    reader = hid.device()
    reader.open_path(path)
    return reader


def probe_mi_02_devices(
    devices: Iterable[dict],
    read_timeout_ms: int = DEFAULT_READ_TIMEOUT_MS,
) -> None:
    """MI_02インターフェイスを直接開いて、受信レポートの形式を診断する。"""
    mi_02_devices = [device for device in devices if is_mi_02_path(device)]
    for device in mi_02_devices:
        reader = None
        print(
            "Probing interface "
            f"{device.get('interface_number')} "
            f"usage_page={device.get('usage_page')} "
            f"usage={device.get('usage')} "
            f"path={device.get('path')}"
        )
        try:
            reader = open_device(device)
            report = reader.read(16, max(1, read_timeout_ms))
            if report:
                print(f"report={format_hex(report)} bytes={len(report)}")
            else:
                print("report=None")
        except Exception as error:
            print(f"open/read error: {error}")
        finally:
            if reader is not None:
                try:
                    reader.close()
                except Exception as error:
                    logging.warning("Failed to close HID device: %s", error)


def read_reports(
    read_timeout_ms: int = DEFAULT_READ_TIMEOUT_MS,
    state_index: int = 2,
) -> None:
    """単純なCLIモードとしてHIDレポートを継続読み取り、状態変化を表示する。"""
    last_state: Optional[bool] = None
    last_report_hex: Optional[str] = None
    reader = None

    while True:
        try:
            if reader is None:
                devices = enumerate_solo_cast_devices()
                selected = select_solo_cast_hid_device(devices)
                if selected is None:
                    logging.warning(
                        "HyperX SoloCast HID device not found (VID=%04X PID=%04X); retrying",
                        VID,
                        PID,
                    )
                    time.sleep(DEFAULT_RECONNECT_DELAY_SECONDS)
                    continue

                print("Selected HID device:")
                print_device(selected)
                reader = open_device(selected)

            report = reader.read(16, read_timeout_ms)
            if not report:
                continue

            report_hex = format_hex(report)
            state = parse_mute_state(report, state_index)
            if report_hex != last_report_hex:
                print(
                    f"report={report_hex} bytes={len(report)} "
                    f"state_index={state_index}"
                )
                last_report_hex = report_hex
            else:
                time.sleep(0.05)

            if state is not None and state != last_state:
                logging.info("Mute state changed: %s", "MUTE" if state else "UNMUTE")
                last_state = state

        except KeyboardInterrupt:
            if reader is not None:
                try:
                    with self._reader_lock:
                        reader.close()
                except Exception:
                    pass
            print("\nHID reader stopped.")
            return
        except (OSError, IOError) as error:
            logging.warning("HID read/open failure: %s; reconnecting", error)
            reader = None
            time.sleep(DEFAULT_RECONNECT_DELAY_SECONDS)
        except Exception as error:
            logging.error("Unexpected HID error: %s; reconnecting", error)
            reader = None
            time.sleep(DEFAULT_RECONNECT_DELAY_SECONDS)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


class SoloCastHidMonitor:
    """HID監視、状態共有、録音エンドポイント制御を行うバックグラウンド監視クラス。"""

    def __init__(
        self,
        read_timeout_ms: int = DEFAULT_READ_TIMEOUT_MS,
        state_index: int = 2,
    ) -> None:
        self.read_timeout_ms = max(1, read_timeout_ms)
        self.state_index = max(0, state_index)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._reader_lock = threading.Lock()
        self._toggle_lock = threading.Lock()
        self._endpoint_lock = threading.Lock()
        self._reader = None
        self._state: Optional[bool] = None
        self._report_hex: Optional[str] = None
        self._connected = False
        self._last_error: Optional[str] = None
        self._updated_at: Optional[str] = None
        self._status_subscribers: set[Queue] = set()

    def start(self) -> None:
        """HID監視スレッドを重複起動せずに開始する。"""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="HyperX-SoloCast-HID",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout_seconds: float = 1.0) -> None:
        """監視ループへ停止要求を送り、必要に応じてHIDデバイスを明示的に閉じる。"""
        self._stop_event.set()
        with self._lock:
            thread = self._thread
            reader = self._reader
        if reader is not None:
            try:
                with self._reader_lock:
                    reader.close()
            except Exception:
                pass
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(0.0, timeout_seconds))

    def snapshot(self) -> dict:
        """SSEやREST APIへ公開する最新の接続・ミュート状態を返す。"""
        with self._lock:
            return {
                "device": "HyperX SoloCast",
                "vid": VID,
                "pid": PID,
                "connected": self._connected,
                "muted": self._state,
                "report_hex": self._report_hex,
                "updated_at": self._updated_at,
                "last_error": self._last_error,
            }

    def subscribe_status(self) -> Queue:
        """購読者へ現在状態を初期通知し、以降の変更通知用キューを登録する。"""
        subscriber = Queue(maxsize=16)
        with self._lock:
            self._status_subscribers.add(subscriber)
            initial_status = {
                "device": "HyperX SoloCast",
                "vid": VID,
                "pid": PID,
                "connected": self._connected,
                "muted": self._state,
                "report_hex": self._report_hex,
                "updated_at": self._updated_at,
                "last_error": self._last_error,
            }
        subscriber.put_nowait(initial_status)
        return subscriber

    def unsubscribe_status(self, subscriber: Queue) -> None:
        with self._lock:
            self._status_subscribers.discard(subscriber)

    def _set_endpoint_mute(self, muted: bool) -> dict:
        """SoloCastのWindows録音キャプチャエンドポイントへミュート設定を適用する。"""
        try:
            from pycaw.pycaw import AudioUtilities
        except ImportError as error:
            return {
                "status": "error",
                "ok": False,
                "muted": None,
                "message": f"pycaw is unavailable: {error}",
            }

        matched_devices = []
        errors = []
        with self._endpoint_lock:
            endpoint_volume = None
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning)
                    capture_devices = AudioUtilities.GetAllDevices(data_flow=1)
                for device in capture_devices:
                    try:
                        friendly_name = str(device.FriendlyName or "")
                        if "solocast" not in friendly_name.lower():
                            continue
                        candidate = device.EndpointVolume
                        candidate.GetMute()
                        endpoint_volume = candidate
                        matched_devices.append(friendly_name)
                        break
                    except Exception as error:
                        errors.append(
                            f"{friendly_name if 'friendly_name' in locals() else 'SoloCast'}: {error}"
                        )
            except Exception as error:
                return {
                    "status": "error",
                    "ok": False,
                    "muted": None,
                    "message": f"Failed to enumerate capture devices: {error}",
                }

            if endpoint_volume is not None:
                try:
                    endpoint_volume.SetMute(bool(muted), None)
                    actual_mute = bool(endpoint_volume.GetMute())
                    if actual_mute == bool(muted):
                        return {
                            "status": "ok",
                            "ok": True,
                            "muted": bool(muted),
                            "matched_devices": matched_devices,
                            "controlled_devices": matched_devices,
                            "errors": errors,
                        }
                    errors.append(f"SoloCast: requested={muted}, actual={actual_mute}")
                except Exception as error:
                    errors.append(f"SoloCast: {error}")
                    endpoint_volume = None

        if matched_devices:
            return {
                "status": "error",
                "ok": False,
                "muted": None,
                "matched_devices": matched_devices,
                "controlled_devices": [],
                "errors": errors,
            }

        return {
            "status": "error",
            "ok": False,
            "muted": None,
            "matched_devices": matched_devices,
            "controlled_devices": [],
            "message": "HyperX SoloCast capture endpoint was not controllable",
            "errors": errors,
        }

    def set_mute(self, muted: bool) -> dict:
        result = self._set_endpoint_mute(bool(muted))
        if result["ok"]:
            self._set_status(
                state=bool(muted),
                connected=True,
                last_error=None,
            )
        return result

    def _get_endpoint_mute(self) -> Optional[bool]:
        """Windows録音エンドポイントから現在のミュート状態を取得する。"""
        try:
            from pycaw.pycaw import AudioUtilities
        except ImportError:
            return None

        with self._endpoint_lock:
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning)
                    capture_devices = AudioUtilities.GetAllDevices(data_flow=1)
            except Exception:
                return None

            for device in capture_devices:
                try:
                    friendly_name = str(device.FriendlyName or "")
                    if "solocast" not in friendly_name.lower():
                        continue
                    endpoint_volume = device.EndpointVolume
                    current = bool(endpoint_volume.GetMute())
                    return current
                except Exception:
                    continue

        return None

    def toggle_mute(self) -> dict:
        """現在値を取得し、その反対のミュート状態へ一度だけ切り替える。"""
        with self._toggle_lock:
            current = self._get_endpoint_mute()
            if current is None:
                return {
                    "status": "error",
                    "ok": False,
                    "muted": None,
                    "message": "Current SoloCast mute state is unavailable",
                }

            desired = not bool(current)
            endpoint_result = self._set_endpoint_mute(desired)
            if endpoint_result["ok"]:
                self._set_status(
                    state=desired,
                    connected=True,
                    last_error=None,
                )
            return endpoint_result

    def _set_status(
        self,
        *,
        state: Optional[bool] = None,
        report_hex: Optional[str] = None,
        connected: Optional[bool] = None,
        last_error: Optional[str] = None,
    ) -> None:
        """状態を更新し、変更時だけ購読者へ通知する。"""
        with self._lock:
            previous_state = self._state
            previous_connection = self._connected
            previous_error = self._last_error
            if state is not None:
                self._state = state
            if report_hex is not None:
                self._report_hex = report_hex
            if connected is not None:
                self._connected = connected
            if last_error is not None:
                self._last_error = last_error
            if state is not None or report_hex is not None:
                self._updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            should_print = state is not None and state != previous_state
            connection_changed = connected is not None and connected != previous_connection
            error_changed = last_error is not None and last_error != previous_error
            should_notify = should_print or connection_changed or error_changed
            notification = None
            if should_notify:
                notification = {
                    "device": "HyperX SoloCast",
                    "vid": VID,
                    "pid": PID,
                    "connected": self._connected,
                    "muted": self._state,
                    "report_hex": self._report_hex,
                    "updated_at": self._updated_at,
                    "last_error": self._last_error,
                }
            subscribers = tuple(self._status_subscribers)

        if notification is not None:
            for subscriber in subscribers:
                try:
                    subscriber.put_nowait(notification)
                except Exception:
                    pass

        if should_print:
            print(
                f"[Mic Controller] Mute state changed: {'MUTE' if state else 'UNMUTE'}",
                flush=True,
            )

    def _run(self) -> None:
        """HIDデバイスへ再接続しながらレポートを読み続ける監視ループ。"""
        reader = None
        while not self._stop_event.is_set():
            try:
                if reader is None:
                    selected = select_solo_cast_hid_device(
                        enumerate_solo_cast_devices()
                    )
                    if selected is None:
                        self._set_status(
                            connected=False,
                            last_error="HyperX SoloCast HID device not found",
                        )
                        self._stop_event.wait(DEFAULT_RECONNECT_DELAY_SECONDS)
                        continue

                    reader = open_device(selected)
                    with self._lock:
                        self._reader = reader
                    self._set_status(connected=True, last_error=None)

                with self._reader_lock:
                    report = reader.read(16, self.read_timeout_ms)
                if self._stop_event.is_set():
                    break
                if not report:
                    continue

                report_hex = format_hex(report)
                state = parse_mute_state(report, self.state_index)
                self._set_status(
                    state=state,
                    report_hex=report_hex,
                    connected=True,
                )
            except Exception as error:
                if self._stop_event.is_set():
                    break
                self._set_status(
                    connected=False,
                    last_error=f"HID read/open failure: {error}",
                )
                if reader is not None:
                    try:
                        with self._reader_lock:
                            reader.close()
                    except Exception:
                        pass
                reader = None
                with self._lock:
                    self._reader = None
                self._stop_event.wait(DEFAULT_RECONNECT_DELAY_SECONDS)

        if reader is not None:
            try:
                reader.close()
            except Exception:
                pass
        with self._lock:
            self._reader = None
            self._connected = False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enumerate and read the HyperX SoloCast HID mute reports."
    )
    parser.add_argument(
        "--enumerate-only",
        action="store_true",
        help="List matching HID devices and exit.",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Open each MI_02 HID collection briefly and print a received report.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=DEFAULT_READ_TIMEOUT_MS,
        help="HID read timeout in milliseconds.",
    )
    parser.add_argument(
        "--state-index",
        type=int,
        default=2,
        help="Report byte index containing 0x01 (muted) or 0x00 (unmuted).",
    )
    args = parser.parse_args()

    configure_logging()

    devices = enumerate_solo_cast_devices()
    if not devices:
        print(f"No HID device found for VID=0x{VID:04X}, PID=0x{PID:04X}")
        return 1 if args.enumerate_only else 0

    print(f"Found {len(devices)} matching HID device(s):")
    for device in devices:
        print_device(device)

    if args.enumerate_only:
        return 0

    if args.probe:
        probe_mi_02_devices(devices, read_timeout_ms=max(1, args.timeout_ms))
        return 0

    read_timeout_ms = max(1, args.timeout_ms)
    state_index = max(0, args.state_index)
    read_reports(read_timeout_ms=read_timeout_ms, state_index=state_index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
