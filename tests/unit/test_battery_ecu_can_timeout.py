import time

from ecu_simulation.battery_ecu import BatteryECU


def test_can_timeout_not_active_at_initialization():
    ecu = BatteryECU()

    assert "CAN_TIMEOUT" not in ecu.check_faults()
    assert ecu.get_dtc() is None


def test_injected_can_timeout_sets_fault_and_dtc():
    ecu = BatteryECU()

    ecu.inject_can_timeout()

    assert "CAN_TIMEOUT" in ecu.check_faults()
    assert ecu.get_dtc() == "BMS_CAN_TIMEOUT_ACTIVE"


def test_clear_can_timeout_removes_fault():
    ecu = BatteryECU()

    ecu.inject_can_timeout()
    ecu.clear_can_timeout()

    assert "CAN_TIMEOUT" not in ecu.check_faults()
    assert ecu.get_dtc() is None


def test_can_timeout_watchdog_requires_recent_can_frame():
    ecu = BatteryECU()
    ecu.config["can_timeout_ms"] = 50

    ecu.receive_can_message(0x100, b"\x00" * 8)
    assert "CAN_TIMEOUT" not in ecu.check_faults()

    time.sleep(0.1)
    assert "CAN_TIMEOUT" in ecu.check_faults()

    ecu.receive_can_message(0x100, b"\x00" * 8)
    assert "CAN_TIMEOUT" not in ecu.check_faults()
