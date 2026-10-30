import unittest
import io
from contextlib import redirect_stdout
from unittest.mock import patch

from soloCastHidReader import (
    SoloCastHidMonitor,
    format_hex,
    is_mi_02_path,
    parse_mute_state,
    select_solo_cast_hid_device,
)


class SoloCastHidReaderTests(unittest.TestCase):
    def test_monitor_initial_snapshot(self):
        monitor = SoloCastHidMonitor()
        snapshot = monitor.snapshot()
        self.assertFalse(snapshot["connected"])
        self.assertIsNone(snapshot["muted"])
        self.assertEqual(snapshot["vid"], 0x03F0)
        self.assertEqual(snapshot["pid"], 0x078B)

    def test_monitor_prints_mute_state_changes(self):
        monitor = SoloCastHidMonitor()

        output = io.StringIO()
        with redirect_stdout(output):
            monitor._set_status(state=False)
            monitor._set_status(state=True)
            monitor._set_status(state=True)

        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("UNMUTE", lines[0])
        self.assertIn("MUTE", lines[1])

    def test_monitor_sets_endpoint_mute(self):
        monitor = SoloCastHidMonitor()
        with patch.object(
            monitor,
            "_set_endpoint_mute",
            return_value={"ok": True, "muted": True},
        ):
            result = monitor.set_mute(True)

        self.assertTrue(result["ok"])
        self.assertTrue(result["muted"])

    def test_monitor_hid_change_synchronizes_endpoint(self):
        monitor = SoloCastHidMonitor()

        with patch.object(
            monitor,
            "_set_endpoint_mute",
            return_value={"ok": True},
        ) as set_endpoint:
            monitor._set_status(state=False)
            monitor._set_status(state=True)

        self.assertFalse(set_endpoint.called)

    def test_toggle_mutes_opposite_state_once(self):
        monitor = SoloCastHidMonitor()
        monitor._set_status(state=False)
        with patch.object(monitor, "_get_endpoint_mute", return_value=False):
            with patch.object(
                monitor,
                "_set_endpoint_mute",
                return_value={"ok": True, "muted": True},
            ):
                result = monitor.toggle_mute()

        self.assertTrue(result["ok"])
        self.assertTrue(result["muted"])
        self.assertTrue(monitor.snapshot()["muted"])

    def test_toggle_unmutes_opposite_state_once(self):
        monitor = SoloCastHidMonitor()
        monitor._set_status(state=True)

        with patch.object(monitor, "_get_endpoint_mute", return_value=True):
            with patch.object(
                monitor,
                "_set_endpoint_mute",
                return_value={"ok": True, "muted": False},
            ):
                result = monitor.toggle_mute()

        self.assertTrue(result["ok"])
        self.assertFalse(result["muted"])
        self.assertFalse(monitor.snapshot()["muted"])

    def test_mute_report(self):
        report = bytes.fromhex("66 81 01 00 00 00 00 00 00 00 00 00 00 00 00 00")
        self.assertTrue(parse_mute_state(report))

    def test_unmute_report(self):
        report = bytes.fromhex("66 81 00 00 00 00 00 00 00 00 00 00 00 00 00 00")
        self.assertFalse(parse_mute_state(report))

    def test_unknown_report(self):
        report = bytes.fromhex("66 81 02 00")
        self.assertIsNone(parse_mute_state(report))

    def test_short_report(self):
        self.assertIsNone(parse_mute_state(b"\x66\x81"))

    def test_report_format(self):
        report = bytes.fromhex("66 81 01")
        self.assertEqual(format_hex(report), "66 81 01")

    def test_select_prefers_mi_02(self):
        devices = [
            {"path": "\\\\?\\hid#vid_03f0&pid_078b&mi_00", "usage_page": 1},
            {"path": "\\\\?\\hid#vid_03f0&pid_078b&mi_02", "usage_page": 12},
        ]
        selected = select_solo_cast_hid_device(devices)
        self.assertTrue(is_mi_02_path(selected))

    def test_select_prefers_vendor_usage_page(self):
        devices = [
            {"path": "\\\\?\\hid#vid_03f0&pid_078b&mi_02&col02", "usage_page": 12},
            {"path": "\\\\?\\hid#vid_03f0&pid_078b&mi_02&col01", "usage_page": 65472},
        ]
        selected = select_solo_cast_hid_device(devices)
        self.assertEqual(selected["usage_page"], 65472)


if __name__ == "__main__":
    unittest.main()
