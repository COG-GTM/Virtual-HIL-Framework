"""Unit tests for the UDS (ISO 14229) diagnostic server."""

import pytest

from ecu_simulation.battery_ecu import BatteryECU
from ecu_simulation.diagnostic_server import DiagnosticServer


@pytest.fixture
async def server() -> DiagnosticServer:
    srv = DiagnosticServer("BMS")
    await srv.start()
    return srv


async def test_session_control_extended(server):
    resp = await server.process_request(bytes([0x10, 0x03]))
    assert (resp.sid, resp.is_negative) == (0x50, False)
    assert resp.data[0] == 0x03


async def test_read_did_software_version(server):
    resp = await server.process_request(bytes([0x22, 0xF1, 0x9E]))
    assert resp.sid == 0x62
    assert resp.data == bytes([0xF1, 0x9E]) + b"1.0.0"


async def test_read_unknown_did_is_request_out_of_range(server):
    resp = await server.process_request(bytes([0x22, 0x12, 0x34]))
    assert resp.is_negative
    assert resp.data == bytes([0x22, 0x31])


async def test_bms_fault_dtc_lifecycle(server):
    """Overvoltage on the BMS -> DTC readable via 0x19 -> cleared via 0x14."""
    ecu = BatteryECU()

    empty = await server.process_request(bytes([0x19, 0x02, 0xFF]))
    assert empty.data == bytes([0x59, 0x02, 0x00])

    ecu.set_cell_voltage(0, 4.35)
    assert "OVERVOLTAGE" in ecu.check_faults()
    server.store_dtc("P0A80", status=0x09)

    stored = await server.process_request(bytes([0x19, 0x02, 0xFF]))
    assert stored.data == bytes([0x59, 0x02, 0x00, 0x02, 0x0A, 0x80, 0x09])

    cleared = await server.process_request(bytes([0x14, 0xFF, 0xFF, 0xFF]))
    assert (cleared.sid, cleared.is_negative) == (0x54, False)
    after = await server.process_request(bytes([0x19, 0x02, 0xFF]))
    assert after.data == bytes([0x59, 0x02, 0x00])


async def test_clear_dtc_rejected_when_dtc_setting_off(server):
    server.store_dtc("P0A80")
    await server.process_request(bytes([0x85, 0x00]))
    resp = await server.process_request(bytes([0x14, 0xFF, 0xFF, 0xFF]))
    assert resp.is_negative
    assert resp.data == bytes([0x14, 0x22])
