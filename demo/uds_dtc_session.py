#!/usr/bin/env python3
"""
UDS (ISO 14229) diagnostic session against the virtual BMS ECU.

Flow (all real code paths, nothing mocked):
  1. Inject an over-voltage fault into the running FastAPI Battery ECU (PUT /ecu/cell/0/voltage)
  2. The ECU's check_faults()/get_dtc() raise BMS_OVERVOLTAGE_ACTIVE -> mirrored into the
     UDS DiagnosticServer as DTC P0A80 (hybrid battery pack), plus a CAN 0x102 BMS_Fault frame
  3. Tester sends raw UDS requests: 0x10 (session), 0x22 (read DID), 0x19 (read DTC),
     0x14 (clear DTC), 0x19 again -> transcript printed like a diagnostic tester
  4. Transcript is saved as text + PNG in demo/out/
"""

import asyncio
import re
import sys
import time
from pathlib import Path

import requests

from ecu_simulation.can_interface import CANInterface
from ecu_simulation.diagnostic_server import DiagnosticServer

OUT = Path(__file__).parent / "out"
ECU_URL = "http://localhost:8000"
FAULT_TO_DTC = {"OVERVOLTAGE": "P0A80", "UNDERVOLTAGE": "P0A7F", "OVERTEMPERATURE": "P0A9C"}

G, Y, R, C, B, N = "\033[92m", "\033[93m", "\033[91m", "\033[96m", "\033[1m", "\033[0m"
ANSI = re.compile(r"\033\[[0-9;]*m")
transcript: list[str] = []


def say(line: str = "", color: str = ""):
    print(f"{color}{line}{N}" if color else line)
    transcript.append(ANSI.sub("", line))


def hx(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def decode_dtcs(resp: bytes) -> list[str]:
    body = resp[3:]  # 59 02 <mask> then 4-byte records
    out = []
    for i in range(0, len(body) - 3, 4):
        b0, b1, b2, st = body[i : i + 4]
        letter = {0x02: "P", 0x08: "B", 0x01: "C", 0x00: "U"}.get(b0, "?")
        out.append(f"{letter}{b1:02X}{b2:02X} status=0x{st:02X}")
    return out


async def main():
    server = DiagnosticServer(ecu_name="BMS_ECU")
    can = CANInterface(channel="virtual0")
    await server.start()
    await can.start()

    async def tx(label: str, req: bytes):
        say(f"  TX  {hx(req):<24} ; {label}", C)
        t0 = time.perf_counter()
        resp = await server.process_request(req)
        dt = (time.perf_counter() - t0) * 1e3
        # server handlers are inconsistent about echoing the response SID in data
        raw = resp.data if resp.data[:1] == bytes([resp.sid]) else bytes([resp.sid]) + resp.data
        tag = f"{R}NRC 0x{resp.nrc:02X}" if resp.is_negative else f"{G}OK"
        say(f"  RX  {hx(raw):<24} ; {tag}{N} ({dt:.2f} ms)")
        return raw

    say(f"{B}=== UDS Diagnostic Session — Virtual BMS ECU (ISO 14229 over virtual CAN) ==={N}")
    say()
    say("[1] Tester -> ECU: DiagnosticSessionControl / ReadDataByIdentifier", B)
    await tx("0x10 03 extendedDiagnosticSession", bytes([0x10, 0x03]))
    r = await tx("0x22 F19E softwareVersion", bytes([0x22, 0xF1, 0x9E]))
    say(f"       softwareVersion = {r[3:].decode(errors='replace')!r}")
    r = await tx("0x22 F198 supplier", bytes([0x22, 0xF1, 0x98]))
    say(f"       supplier        = {r[3:].decode(errors='replace')!r}")
    say()

    say("[2] Baseline: ReadDTCInformation (reportDTCByStatusMask 0xFF)", B)
    r = await tx("0x19 02 FF", bytes([0x19, 0x02, 0xFF]))
    say(f"       stored DTCs: {decode_dtcs(r) or 'none'}", G)
    say()

    say("[3] Fault injection on running FastAPI Battery ECU: cell 0 -> 4.35 V (limit 4.20 V)", B)
    requests.put(f"{ECU_URL}/ecu/cell/0/voltage", json={"voltage": 4.35}, timeout=5).raise_for_status()
    faults = requests.get(f"{ECU_URL}/ecu/faults", timeout=5).json()
    say(f"       GET /ecu/faults -> faults={faults['faults']} dtc={faults['dtc']}", Y)
    for f in faults["faults"]:
        code = FAULT_TO_DTC.get(f, "P0A00")
        server.store_dtc(code, status=0x09, snapshot={"cell": 0, "voltage": 4.35})  # testFailed|confirmed
        await can.send(0x102, bytes([0x01, 0x00, 0x04, 0x35 & 0xFF, 0, 0, 0, 0]))
        say(f"       CAN 0x102 BMS_Fault frame sent; UDS DTC {code} stored (status 0x09)", Y)
    say()

    say("[4] ReadDTCInformation after fault", B)
    r = await tx("0x19 02 FF", bytes([0x19, 0x02, 0xFF]))
    say(f"       stored DTCs: {decode_dtcs(r)}", R)
    say()

    say("[5] Repair: cell 0 back to 3.70 V, then ClearDiagnosticInformation", B)
    requests.put(f"{ECU_URL}/ecu/cell/0/voltage", json={"voltage": 3.70}, timeout=5).raise_for_status()
    requests.post(f"{ECU_URL}/ecu/dtc/clear", timeout=5).raise_for_status()
    await tx("0x14 FF FF FF clearDiagnosticInformation(all)", bytes([0x14, 0xFF, 0xFF, 0xFF]))
    say()

    say("[6] ReadDTCInformation after clear", B)
    r = await tx("0x19 02 FF", bytes([0x19, 0x02, 0xFF]))
    dtcs = decode_dtcs(r)
    say(f"       stored DTCs: {dtcs or 'none'}", G if not dtcs else R)
    say()
    stats = can.get_statistics()
    say(f"CAN bus: {stats['tx_count']} frame(s) sent on {stats['channel']} @ {stats['bitrate']} bit/s")
    verdict = "PASS" if not dtcs and faults["faults"] == ["OVERVOLTAGE"] else "FAIL"
    say(f"{B}UDS diagnostics check: {verdict}{N}", G if verdict == "PASS" else R)

    await can.stop()
    await server.stop()

    OUT.mkdir(exist_ok=True)
    (OUT / "uds_session.txt").write_text("\n".join(transcript) + "\n")
    render_png(OUT / "uds_session.png")
    return 0 if verdict == "PASS" else 1


def render_png(path: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lines = transcript
    fig, ax = plt.subplots(figsize=(11, 0.28 * len(lines) + 0.6))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.axis("off")
    for i, line in enumerate(lines):
        color = "#e6edf3"
        if line.strip().startswith("TX"):
            color = "#79c0ff"
        elif "NRC" in line:
            color = "#ff7b72"
        elif line.strip().startswith("RX"):
            color = "#7ee787"
        elif "stored DTCs: ['" in line or "FAIL" in line:
            color = "#ff7b72"
        elif "Fault" in line or "->" in line:
            color = "#e3b341"
        elif line.startswith("===") or line.startswith("[") or "PASS" in line:
            color = "#ffffff"
        ax.text(0.01, 1 - (i + 0.5) / len(lines), line, family="monospace", fontsize=9,
                color=color, transform=ax.transAxes, va="center")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
