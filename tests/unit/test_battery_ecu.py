"""Unit tests for the Battery ECU plant model."""

import pytest

from ecu_simulation.battery_ecu import BatteryECU


@pytest.fixture
def ecu() -> BatteryECU:
    return BatteryECU()


def test_soc_calculation(ecu):
    ecu.simulate_charge(current=-100.0, duration=3600)
    # 100 Ah out of a 96 x 3.2 Ah = 307.2 Ah pack
    assert ecu.get_soc() == pytest.approx(100 - 100 / 307.2 * 100)


def test_soc_is_clamped(ecu):
    ecu.simulate_charge(current=50.0, duration=3600)
    assert ecu.get_soc() == 100
    ecu.simulate_charge(current=-1000.0, duration=36000)
    assert ecu.get_soc() == 0


def test_pack_voltage_is_sum_of_cells(ecu):
    assert ecu.get_pack_voltage() == pytest.approx(sum(c.voltage for c in ecu.cells.values()))


@pytest.mark.parametrize(
    ("setter", "value", "fault"),
    [
        ("set_cell_voltage", 4.35, "OVERVOLTAGE"),
        ("set_cell_voltage", 2.5, "UNDERVOLTAGE"),
        ("set_cell_temperature", 70.0, "OVERTEMPERATURE"),
        ("set_cell_temperature", -30.0, "UNDERTEMPERATURE"),
    ],
)
def test_fault_detection_and_recovery(ecu, setter, value, fault):
    assert ecu.check_faults() == []
    getattr(ecu, setter)(0, value)
    assert fault in ecu.check_faults()
    assert ecu.get_dtc() == f"BMS_{ecu.check_faults()[0]}_ACTIVE"
    getattr(ecu, setter)(0, 3.7 if setter == "set_cell_voltage" else 25.0)
    assert ecu.check_faults() == []
    assert ecu.get_dtc() is None


def test_balancing_reduces_spread(ecu):
    ecu.set_cell_voltage(0, 4.1)
    ecu.set_cell_voltage(1, 3.3)
    spread = ecu.state.max_cell_voltage - ecu.state.min_cell_voltage
    ecu.balance_cells()
    assert ecu.state.max_cell_voltage - ecu.state.min_cell_voltage < spread
