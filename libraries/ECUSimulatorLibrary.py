"""
Robot Framework Library for ECU Simulation

This library provides keywords for interacting with virtual ECU simulations
in Robot Framework tests.
"""

import logging
import time
from typing import Optional, Union
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn

logger = logging.getLogger(__name__)


@library
class ECUSimulatorLibrary:
    """
    Robot Framework library for ECU simulation control.

    Provides keywords for:
    - Starting and stopping ECU simulations
    - Reading and controlling ECU state
    - Verifying ECU behavior
    """

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_LIBRARY_VERSION = "0.1.0"

    def __init__(self):
        """Initialize the ECU Simulator Library"""
        self._battery_ecu = None
        self._door_ecu = None
        self._can_interface = None
        self._diag_server = None
        self._running = False

    @keyword
    def start_battery_simulation(self, num_cells: int = 96) -> str:
        """
        Start the battery ECU simulation

        Arguments:
            num_cells: Number of battery cells to simulate

        Returns:
            Simulation instance ID

        Example:
            | ${id}= | Start Battery Simulation | num_cells=96 |
        """
        if self._battery_ecu is None:
            from ecu_simulation.battery_ecu import BatteryECU

            self._battery_ecu = BatteryECU()
            logger.info(f"Started battery simulation with {num_cells} cells")
        return "battery_ecu"

    @keyword
    def start_door_simulation(self, num_doors: int = 4) -> str:
        """
        Start the door ECU simulation

        Arguments:
            num_doors: Number of doors to simulate

        Returns:
            Simulation instance ID

        Example:
            | ${id}= | Start Door Simulation | num_doors=4 |
        """
        if self._door_ecu is None:
            from ecu_simulation.door_ecu import DoorECU

            self._door_ecu = DoorECU(num_doors=num_doors)
            logger.info(f"Started door simulation with {num_doors} doors")
        return "door_ecu"

    @keyword
    def stop_all_simulations(self):
        """Stop all running ECU simulations

        Example:
            | Stop All Simulations |
        """
        self._battery_ecu = None
        self._door_ecu = None
        self._running = False
        logger.info("Stopped all simulations")

    @keyword
    def get_battery_soc(self) -> float:
        """
        Get the current State of Charge (SOC) from battery ECU

        Returns:
            SOC percentage (0-100)

        Example:
            | ${soc}= | Get Battery SOC |
            | Should Be True | ${soc} > 80 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        return self._battery_ecu.get_soc()

    @keyword
    def get_battery_voltage(self) -> float:
        """
        Get the current pack voltage from battery ECU

        Returns:
            Voltage in Volts

        Example:
            | ${voltage}= | Get Battery Voltage |
            | Log | Pack voltage: ${voltage}V |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        return self._battery_ecu.get_pack_voltage()

    @keyword
    def get_battery_temperature(self) -> float:
        """
        Get the current pack temperature from battery ECU

        Returns:
            Temperature in Celsius

        Example:
            | ${temp}= | Get Battery Temperature |
            | Should Be True | ${temp} < 50 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        return self._battery_ecu.get_pack_temperature()

    @keyword
    def get_cell_voltage(self, cell_id: int) -> float:
        """
        Get voltage of a specific battery cell

        Arguments:
            cell_id: Cell identifier

        Returns:
            Cell voltage in Volts

        Example:
            | ${voltage}= | Get Cell Voltage | cell_id=0 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        return self._battery_ecu.get_cell_voltage(cell_id)

    @keyword
    def set_cell_voltage(self, cell_id: int, voltage: float):
        """
        Set voltage of a specific battery cell (fault injection)

        Example:
            | Set Cell Voltage | cell_id=0 | voltage=4.3 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        self._battery_ecu.set_cell_voltage(int(cell_id), float(voltage))

    @keyword
    def set_cell_temperature(self, cell_id: int, temperature: float):
        """
        Set temperature of a specific battery cell (fault injection)

        Example:
            | Set Cell Temperature | cell_id=0 | temperature=70 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        self._battery_ecu.set_cell_temperature(int(cell_id), float(temperature))

    @keyword
    def get_cell_temperature(self, cell_id: int) -> float:
        """
        Get temperature of a specific battery cell

        Example:
            | ${temp}= | Get Cell Temperature | cell_id=0 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        return float(self._battery_ecu.get_cell_temperature(int(cell_id)))

    @keyword
    def get_battery_faults(self) -> list[str]:
        """
        Get list of active battery fault codes

        Example:
            | ${faults}= | Get Battery Faults |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        return list(self._battery_ecu.check_faults())

    @keyword
    def get_battery_ecu_instance(self):
        """
        Return the running BatteryECU instance (for FaultInjectionLibrary)

        Example:
            | ${ecu}= | Get Battery ECU Instance |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        return self._battery_ecu

    @keyword
    def simulate_charging(self, current: float, duration: float):
        """
        Simulate battery charging or discharging

        Arguments:
            current: Current in Amps (positive = charging)
            duration: Duration in seconds

        Example:
            | Simulate Charging | current=10 | duration=60 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        self._battery_ecu.simulate_charge(current, duration)
        logger.info(f"Simulated charging: {current}A for {duration}s")

    @keyword
    def balance_cells(self):
        """Trigger cell balancing in battery ECU

        Example:
            | Balance Cells |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")
        self._battery_ecu.balance_cells()
        logger.info("Cell balancing triggered")

    @keyword
    def get_door_position(self, door_id: int) -> str:
        """
        Get current position of a door

        Arguments:
            door_id: Door identifier (0-3)

        Returns:
            Position state (CLOSED, OPEN, OPENING, CLOSING, BLOCKED, FAULT)

        Example:
            | ${position}= | Get Door Position | door_id=0 |
            | Should Be Equal | ${position} | CLOSED |
        """
        if self._door_ecu is None:
            raise RuntimeError("Door ECU not started")
        return self._door_ecu.get_door_position(door_id).value

    @keyword
    def open_door(self, door_id: int, target_percentage: float = 100.0):
        """
        Open a door to specified percentage

        Arguments:
            door_id: Door identifier (0-3)
            target_percentage: How open to make the door (0-100)

        Example:
            | Open Door | door_id=0 | target_percentage=100 |
        """
        import asyncio

        if self._door_ecu is None:
            raise RuntimeError("Door ECU not started")

        # Run async function in event loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._door_ecu.open_door(door_id, target_percentage))
        logger.info(f"Opened door {door_id} to {target_percentage}%")

    @keyword
    def close_door(self, door_id: int):
        """
        Close a door

        Arguments:
            door_id: Door identifier (0-3)

        Example:
            | Close Door | door_id=0 |
        """
        import asyncio

        if self._door_ecu is None:
            raise RuntimeError("Door ECU not started")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._door_ecu.close_door(door_id))
        logger.info(f"Closed door {door_id}")

    @keyword
    def lock_door(self, door_id: int):
        """
        Lock a door

        Arguments:
            door_id: Door identifier (0-3)

        Example:
            | Lock Door | door_id=0 |
        """
        import asyncio

        if self._door_ecu is None:
            raise RuntimeError("Door ECU not started")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._door_ecu.lock_door(door_id))
        logger.info(f"Locked door {door_id}")

    @keyword
    def unlock_door(self, door_id: int):
        """
        Unlock a door

        Arguments:
            door_id: Door identifier (0-3)

        Example:
            | Unlock Door | door_id=0 |
        """
        import asyncio

        if self._door_ecu is None:
            raise RuntimeError("Door ECU not started")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._door_ecu.unlock_door(door_id))
        logger.info(f"Unlocked door {door_id}")

    @keyword
    def is_door_locked(self, door_id: int) -> bool:
        """
        Check if a door is locked

        Arguments:
            door_id: Door identifier (0-3)

        Returns:
            True if locked, False otherwise

        Example:
            | ${locked}= | Is Door Locked | door_id=0 |
            | Should Be True | ${locked} |
        """
        if self._door_ecu is None:
            raise RuntimeError("Door ECU not started")
        return self._door_ecu.is_locked(door_id)

    @keyword
    def verify_battery_faults(self, expected_faults: list) -> bool:
        """
        Verify battery ECU has expected faults

        Arguments:
            expected_faults: List of expected fault names

        Returns:
            True if faults match

        Example:
            | ${result}= | Verify Battery Faults | ['OVERVOLTAGE'] |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not started")

        actual_faults = self._battery_ecu.check_faults()
        return set(actual_faults) == set(expected_faults)

    @keyword
    def wait_for_door_position(
        self, door_id: int, expected_position: str, timeout: float = 5.0
    ) -> bool:
        """
        Wait for door to reach expected position

        Arguments:
            door_id: Door identifier (0-3)
            expected_position: Expected position state
            timeout: Maximum time to wait in seconds

        Returns:
            True if position reached, False if timeout

        Example:
            | ${result}= | Wait For Door Position | door_id=0 | expected_position=OPEN | timeout=5 |
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            position = self.get_door_position(door_id)
            if position == expected_position:
                return True
            time.sleep(0.1)
        return False


if __name__ == "__main__":
    # Test the library
    lib = ECUSimulatorLibrary()

    print("Testing ECU Simulator Library...")
    lib.start_battery_simulation()
    print(f"Battery SOC: {lib.get_battery_soc()}%")

    lib.start_door_simulation()
    print(f"Door 0 position: {lib.get_door_position(0)}")
    print(f"Door 0 locked: {lib.is_door_locked(0)}")

    lib.stop_all_simulations()
    print("Library test complete")
