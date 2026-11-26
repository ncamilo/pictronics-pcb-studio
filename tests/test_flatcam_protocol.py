"""Independent checks of the vendored pure GRBL parser; no hardware."""
import pytest

from pcb_studio.vendor.flatcam import grbl_protocol as protocol


@pytest.mark.parametrize("state", ["Idle", "Run", "Alarm", "Hold", "Jog", "Door"])
def test_status_state(state):
    report = protocol.parse_grbl_status_report(f"<{state}|MPos:1,2,-3|FS:100,500>")
    assert report["state"] == state
    assert report["mpos"] == (1, 2, -3)
    assert report["feed"] == 100
    assert report["spindle"] == 500


@pytest.mark.parametrize("line", ["ok", "", "<Idle|MPos:1,2>", "<Run|MPos:nan,0,0>",
                                  "<Idle|MPos:0,0,0,0>", "<Idle|WCO:0,inf,0>"])
def test_malformed_report(line):
    assert protocol.parse_grbl_status_report(line) is None


def test_work_position():
    report = protocol.parse_grbl_status_report("<Idle|MPos:10,20,30|WCO:1,2,3>")
    assert protocol.work_position(report) == (9, 18, 27)
    assert protocol.work_position({"mpos": (10, 20, 30)}) is None


def test_successful_probe():
    assert protocol.parse_grbl_probe_output("ok\n[PRB:1,2,-0.3:1]\n") == [(1, 2, -0.3)]


@pytest.mark.parametrize("reply", ["[PRB:1,2,-0.3:0]", "[PRB:1,2,nan:1]"])
def test_failed_probe(reply):
    with pytest.raises(ValueError):
        protocol.parse_grbl_probe_output(reply)


def test_error_and_alarm():
    assert protocol.grbl_reply_error("ok\nALARM:4") == "ALARM:4"
    assert protocol.grbl_reply_error("error:2") == "error:2"
    assert protocol.grbl_reply_error("ok") is None


def test_work_offset():
    assert protocol.parse_grbl_work_offset("[G54:1,2,3]\n[G92:4,5,6]\n[TLO:2]") == (5, 7, 11)


def test_inch_reporting():
    assert protocol.grbl_report_scale("MM", True) == 25.4
    assert protocol.grbl_report_scale("MM", False) == 1.0
