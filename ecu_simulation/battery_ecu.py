"""Battery ECU Simulation Module"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class BatteryCell:
    """Represents a single battery cell"""

    id: int
    voltage: float = 3.7  # Volts
    temperature: float = 25.0  # Celsius
    capacity: float = 3.2  # Ah


@dataclass
class BatteryPackState:
    """Current state of the battery pack"""

    soc: float = 100.0  # State of Charge (%)
    soh: float = 100.0  # State of Health (%)
    voltage: float = 400.0  # Total pack voltage (V)
    current: float = 0.0  # Current (A), positive = charging
    temperature: float = 25.0  # Average temperature (C)
    max_cell_temp: float = 25.0
    min_cell_temp: float = 25.0
    max_cell_voltage: float = 3.7
    min_cell_voltage: float = 3.7


class BatteryECU:
    """
    Simulates a Battery Management System (BMS) ECU.

    Features:
    - Cell-level voltage and temperature monitoring
    - State of Charge (SOC) estimation
    - Cell balancing control
    - Thermal management
    - Fault detection and reporting
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize Battery ECU with optional configuration file"""
        self.cells: Dict[int, BatteryCell] = {}
        self.state = BatteryPackState()
        self.running = False
        self.config = self._load_config(config_path)
        self.last_can_rx_time: float = time.time()
        self._can_timeout_injected: bool = False
        self._can_rx_seen: bool = False
        self._initialize_cells()

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from YAML file"""
        default_config = {
            "num_cells": 96,
            "cell_capacity": 3.2,
            "nominal_voltage": 3.7,
            "max_voltage": 4.2,
            "min_voltage": 2.8,
            "max_temperature": 60.0,
            "min_temperature": -20.0,
            "can_timeout_ms": 500,
        }

        if config_path:
            try:
                with open(config_path, "r") as f:
                    return yaml.safe_load(f)
            except FileNotFoundError:
                logger.warning(f"Config file not found: {config_path}")

        return default_config

    def _initialize_cells(self):
        """Initialize battery cells with default values"""
        for i in range(self.config["num_cells"]):
            self.cells[i] = BatteryCell(
                id=i,
                voltage=self.config["nominal_voltage"] + (i % 10) * 0.01,
                temperature=25.0 + (i % 5),
                capacity=self.config["cell_capacity"],
            )
        self._update_pack_state()

    def _update_pack_state(self):
        """Update pack-level state from individual cells"""
        if not self.cells:
            return

        voltages = [cell.voltage for cell in self.cells.values()]
        temperatures = [cell.temperature for cell in self.cells.values()]

        self.state.voltage = sum(voltages)
        self.state.current = 0.0  # Would be calculated from power flow
        self.state.temperature = sum(temperatures) / len(temperatures)
        self.state.max_cell_temp = max(temperatures)
        self.state.min_cell_temp = min(temperatures)
        self.state.max_cell_voltage = max(voltages)
        self.state.min_cell_voltage = min(voltages)

    def get_cell_voltage(self, cell_id: int) -> float:
        """Get voltage of specific cell"""
        return self.cells.get(cell_id, BatteryCell(id=cell_id)).voltage

    def get_cell_temperature(self, cell_id: int) -> float:
        """Get temperature of specific cell"""
        return self.cells.get(cell_id, BatteryCell(id=cell_id)).temperature

    def get_soc(self) -> float:
        """Get current State of Charge"""
        return self.state.soc

    def get_soh(self) -> float:
        """Get current State of Health"""
        return self.state.soh

    def get_pack_voltage(self) -> float:
        """Get total pack voltage"""
        return self.state.voltage

    def get_pack_current(self) -> float:
        """Get pack current"""
        return self.state.current

    def get_pack_temperature(self) -> float:
        """Get average pack temperature"""
        return self.state.temperature

    def receive_can_message(self, can_id: int, data: bytes):
        """Register a received CAN frame (refreshes the bus-alive watchdog)"""
        del can_id, data
        self.last_can_rx_time = time.time()
        self._can_rx_seen = True

    def inject_can_timeout(self):
        """Inject a CAN bus timeout fault"""
        self._can_timeout_injected = True

    def clear_can_timeout(self):
        """Clear an injected CAN bus timeout fault"""
        self._can_timeout_injected = False
        self.last_can_rx_time = time.time()
        self._can_rx_seen = False

    def is_can_timeout_active(self) -> bool:
        """Check whether the CAN bus timeout fault is active"""
        return self._can_timeout_injected or (
            self._can_rx_seen
            and (time.time() - self.last_can_rx_time) * 1000
            > self.config.get("can_timeout_ms", 500)
        )

    def set_cell_voltage(self, cell_id: int, voltage: float):
        """Set voltage of specific cell (for testing/fault injection)"""
        if cell_id in self.cells:
            self.cells[cell_id].voltage = voltage
            self._update_pack_state()

    def set_cell_temperature(self, cell_id: int, temperature: float):
        """Set temperature of specific cell (for testing/fault injection)"""
        if cell_id in self.cells:
            self.cells[cell_id].temperature = temperature
            self._update_pack_state()

    def simulate_charge(self, current: float, duration: float):
        """
        Simulate charging/discharging
        Args:
            current: Current in Amps (positive = charging)
            duration: Duration in seconds
        """
        # Calculate energy transferred
        energy = current * duration  # Amp-seconds
        capacity_change = energy / 3600  # Convert to Ah

        # Update SOC based on capacity
        total_capacity = self.config["num_cells"] * self.config["cell_capacity"]
        soc_change = (capacity_change / total_capacity) * 100
        self.state.soc = max(0, min(100, self.state.soc + soc_change))

        # Simulate voltage changes due to charge/discharge
        voltage_factor = 1 + (current * 0.001)
        for cell in self.cells.values():
            cell.voltage *= voltage_factor
            cell.voltage = max(
                self.config["min_voltage"], min(self.config["max_voltage"], cell.voltage)
            )

        self._update_pack_state()

    def balance_cells(self):
        """Simulate cell balancing - equalize cell voltages"""
        if not self.cells:
            return

        avg_voltage = sum(c.voltage for c in self.cells.values()) / len(self.cells)
        for cell in self.cells.values():
            # Move cell voltage towards average
            cell.voltage += (avg_voltage - cell.voltage) * 0.1

        self._update_pack_state()

    def check_faults(self) -> list:
        """Check for battery system faults"""
        faults = []

        # Check for overvoltage
        if self.state.max_cell_voltage > self.config["max_voltage"]:
            faults.append("OVERVOLTAGE")

        # Check for undervoltage
        if self.state.min_cell_voltage < self.config["min_voltage"]:
            faults.append("UNDERVOLTAGE")

        # Check for overtemperature
        if self.state.max_cell_temp > self.config["max_temperature"]:
            faults.append("OVERTEMPERATURE")

        # Check for undertemperature
        if self.state.min_cell_temp < self.config["min_temperature"]:
            faults.append("UNDERTEMPERATURE")

        # Check for low SOC
        if self.state.soc < 10:
            faults.append("LOW_SOC")

        if self.is_can_timeout_active():
            faults.append("CAN_TIMEOUT")

        return faults

    def get_dtc(self) -> Optional[str]:
        """Get Diagnostic Trouble Code if any fault exists"""
        faults = self.check_faults()
        if faults:
            return f"BMS_{faults[0]}_ACTIVE"
        return None

    def clear_dtc(self):
        """Clear any stored DTCs (simulation only)"""
        # In real implementation, would clear stored fault codes
        self.clear_can_timeout()

    async def start(self):
        """Start the ECU simulation"""
        self.running = True
        logger.info("Battery ECU simulation started")

    async def stop(self):
        """Stop the ECU simulation"""
        self.running = False
        logger.info("Battery ECU simulation stopped")

    def to_dict(self) -> dict:
        """Export current state as dictionary"""
        return {
            "soc": self.state.soc,
            "soh": self.state.soh,
            "voltage": self.state.voltage,
            "current": self.state.current,
            "temperature": self.state.temperature,
            "max_cell_temp": self.state.max_cell_temp,
            "min_cell_temp": self.state.min_cell_temp,
            "max_cell_voltage": self.state.max_cell_voltage,
            "min_cell_voltage": self.state.min_cell_voltage,
            "can_timeout": self.is_can_timeout_active(),
            "faults": self.check_faults(),
        }


if __name__ == "__main__":
    # Quick test of the Battery ECU
    async def main():
        ecu = BatteryECU()
        await ecu.start()

        print(f"Initial SOC: {ecu.get_soc()}%")
        print(f"Pack Voltage: {ecu.get_pack_voltage()}V")
        print(f"Faults: {ecu.check_faults()}")

        # Simulate charging
        ecu.simulate_charge(10.0, 3600)
        print(f"After charging - SOC: {ecu.get_soc()}%")

        await ecu.stop()

    asyncio.run(main())
