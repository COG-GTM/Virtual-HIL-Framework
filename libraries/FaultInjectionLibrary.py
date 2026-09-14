"""
Robot Framework Library for Fault Injection

This library provides keywords for injecting faults into ECUs
for testing purposes in Robot Framework tests.
"""

import logging
import time
from typing import Optional, List
from robot.api.deco import keyword, library

logger = logging.getLogger(__name__)


@library
class FaultInjectionLibrary:
    """
    Robot Framework library for fault injection testing.

    Provides keywords for:
    - Injecting battery faults
    - Injecting door ECU faults
    - Injecting CAN bus faults
    - Verifying fault detection
    - Clearing faults
    """

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_LIBRARY_VERSION = "0.1.0"

    def __init__(self):
        """Initialize the Fault Injection Library"""
        self._battery_ecu = None
        self._door_ecu = None
        self._can_interface = None
        self._injected_faults = []

    @keyword
    def set_battery_ecu(self, battery_ecu):
        """
        Set the battery ECU instance for fault injection

        Arguments:
            battery_ecu: BatteryECU instance

        Example:
            | Set Battery ECU | ${battery_instance} |
        """
        self._battery_ecu = battery_ecu

    @keyword
    def set_door_ecu(self, door_ecu):
        """
        Set the door ECU instance for fault injection

        Arguments:
            door_ecu: DoorECU instance

        Example:
            | Set Door ECU | ${door_instance} |
        """
        self._door_ecu = door_ecu

    @keyword
    def inject_cell_overvoltage(self, cell_id: int, voltage: float = 4.3):
        """
        Inject overvoltage fault on a battery cell

        Arguments:
            cell_id: Cell identifier
            voltage: Voltage to set (default 4.3V, above typical max of 4.2V)

        Example:
            | Inject Cell Overvoltage | cell_id=0 | voltage=4.3 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")

        self._battery_ecu.set_cell_voltage(cell_id, voltage)
        self._injected_faults.append(("cell_overvoltage", cell_id))
        logger.warning(f"Injected overvoltage on cell {cell_id}: {voltage}V")

    @keyword
    def inject_cell_undervoltage(self, cell_id: int, voltage: float = 2.5):
        """
        Inject undervoltage fault on a battery cell

        Arguments:
            cell_id: Cell identifier
            voltage: Voltage to set (default 2.5V, below typical min of 2.8V)

        Example:
            | Inject Cell Undervoltage | cell_id=0 | voltage=2.5 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")

        self._battery_ecu.set_cell_voltage(cell_id, voltage)
        self._injected_faults.append(("cell_undervoltage", cell_id))
        logger.warning(f"Injected undervoltage on cell {cell_id}: {voltage}V")

    @keyword
    def inject_cell_overtemperature(self, cell_id: int, temperature: float = 70.0):
        """
        Inject overheating fault on a battery cell

        Arguments:
            cell_id: Cell identifier
            temperature: Temperature to set in Celsius (default 70°C)

        Example:
            | Inject Cell Overtemperature | cell_id=0 | temperature=70 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")

        self._battery_ecu.set_cell_temperature(cell_id, temperature)
        self._injected_faults.append(("cell_overtemperature", cell_id))
        logger.warning(f"Injected overtemperature on cell {cell_id}: {temperature}°C")

    @keyword
    def inject_cell_undertemperature(self, cell_id: int, temperature: float = -25.0):
        """
        Inject undertemperature fault on a battery cell

        Arguments:
            cell_id: Cell identifier
            temperature: Temperature to set in Celsius (default -25°C)

        Example:
            | Inject Cell Undertemperature | cell_id=0 | temperature=-25 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")

        self._battery_ecu.set_cell_temperature(cell_id, temperature)
        self._injected_faults.append(("cell_undertemperature", cell_id))
        logger.warning(f"Injected undertemperature on cell {cell_id}: {temperature}°C")

    @keyword
    def inject_low_soc(self, soc: float = 5.0):
        """
        Inject low SOC fault

        Arguments:
            soc: SOC to set (default 5%)

        Example:
            | Inject Low SOC | soc=5 |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")

        # Set SOC by simulating heavy discharge
        original_soc = self._battery_ecu.get_soc()
        discharge_amount = (original_soc - soc) / 100 * 96 * 3.2 * 3600 / 100  # Approximate
        self._battery_ecu.simulate_charge(-discharge_amount, 1)

        self._injected_faults.append(("low_soc", None))
        logger.warning(f"Injected low SOC: {soc}%")

    @keyword
    def inject_door_block(self, door_id: int):
        """
        Inject door block fault (trigger pinch protection)

        Arguments:
            door_id: Door identifier (0-3)

        Example:
            | Inject Door Block | door_id=0 |
        """
        if self._door_ecu is None:
            raise RuntimeError("Door ECU not set")

        self._door_ecu.trigger_pinch(door_id)
        self._injected_faults.append(("door_block", door_id))
        logger.warning(f"Injected block fault on door {door_id}")

    @keyword
    def inject_door_ecu_fault(self, door_id: Optional[int] = None):
        """
        Inject general door ECU fault state

        Arguments:
            door_id: Optional door ID (if None, affects all doors)

        Example:
            | Inject Door ECU Fault | door_id=0 |
        """
        if self._door_ecu is None:
            raise RuntimeError("Door ECU not set")

        self._door_ecu.set_fault_state(True)
        self._injected_faults.append(("door_ecu_fault", door_id))
        logger.warning(f"Injected ECU fault on door {door_id if door_id is not None else 'all'}")

    @keyword
    def inject_can_bus_off(self):
        """
        Simulate CAN bus-off state

        Example:
            | Inject CAN Bus Off |
        """
        self._injected_faults.append(("can_bus_off", None))
        logger.warning("Injected CAN bus-off fault")
        # Note: In real implementation, this would affect the CAN interface

    @keyword
    def inject_can_bus_timeout(self):
        """
        Inject CAN bus timeout fault on the battery ECU

        Example:
            | Inject CAN Bus Timeout |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")

        self._battery_ecu.inject_can_timeout()
        self._injected_faults.append(("can_bus_timeout", None))
        logger.warning("Injected CAN bus timeout fault")

    @keyword
    def clear_can_bus_timeout(self):
        """
        Clear CAN bus timeout fault on the battery ECU

        Example:
            | Clear CAN Bus Timeout |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")

        self._battery_ecu.clear_can_timeout()
        self._injected_faults = [
            fault for fault in self._injected_faults if fault[0] != "can_bus_timeout"
        ]
        logger.info("Cleared CAN bus timeout fault")

    @keyword
    def inject_can_frame_loss(self, can_id: int, loss_rate: float = 0.5):
        """
        Simulate CAN frame loss for specific message ID

        Arguments:
            can_id: CAN message ID
            loss_rate: Percentage of frames to lose (0.0-1.0)

        Example:
            | Inject CAN Frame Loss | can_id=0x100 | loss_rate=0.5 |
        """
        self._injected_faults.append(("can_frame_loss", (can_id, loss_rate)))
        logger.warning(f"Injected {loss_rate * 100}% frame loss for CAN ID 0x{can_id:03X}")

    @keyword
    def inject_can_signal_corruption(self, can_id: int, bit_offset: int = 0):
        """
        Simulate CAN signal corruption

        Arguments:
            can_id: CAN message ID
            bit_offset: Bit offset to corrupt

        Example:
            | Inject CAN Signal Corruption | can_id=0x100 | bit_offset=0 |
        """
        self._injected_faults.append(("can_signal_corruption", (can_id, bit_offset)))
        logger.warning(f"Injected signal corruption for CAN ID 0x{can_id:03X}")

    @keyword
    def verify_battery_fault_detected(self, fault_name: str, timeout: float = 2.0) -> bool:
        """
        Verify that a battery fault was detected

        Arguments:
            fault_name: Name of fault to check (OVERVOLTAGE, UNDERVOLTAGE, etc.)
            timeout: Maximum time to wait in seconds

        Returns:
            True if fault detected

        Example:
            | ${detected}= | Verify Battery Fault Detected | fault_name=OVERVOLTAGE |
            | Should Be True | ${detected} |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")

        start_time = time.time()
        while time.time() - start_time < timeout:
            faults = self._battery_ecu.check_faults()
            if fault_name in faults:
                logger.info(f"Fault '{fault_name}' detected")
                return True
            time.sleep(0.1)

        logger.error(f"Fault '{fault_name}' not detected within {timeout}s")
        return False

    @keyword
    def verify_door_fault_detected(self, door_id: int, timeout: float = 2.0) -> bool:
        """
        Verify that a door fault was detected

        Arguments:
            door_id: Door identifier
            timeout: Maximum time to wait in seconds

        Returns:
            True if fault detected

        Example:
            | ${detected}= | Verify Door Fault Detected | door_id=0 |
            | Should Be True | ${detected} |
        """
        if self._door_ecu is None:
            raise RuntimeError("Door ECU not set")

        start_time = time.time()
        while time.time() - start_time < timeout:
            faults = self._door_ecu.get_faults()
            if any(f"DOOR_{door_id}" in fault for fault in faults):
                logger.info(f"Door {door_id} fault detected")
                return True
            time.sleep(0.1)

        logger.error(f"Door {door_id} fault not detected within {timeout}s")
        return False

    @keyword
    def get_battery_dtc(self) -> Optional[str]:
        """
        Get current DTC from battery ECU

        Returns:
            DTC string or None

        Example:
            | ${dtc}= | Get Battery DTC |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")
        return self._battery_ecu.get_dtc()

    @keyword
    def get_door_dtc(self) -> Optional[str]:
        """
        Get current DTC from door ECU

        Returns:
            DTC string or None

        Example:
            | ${dtc}= | Get Door DTC |
        """
        if self._door_ecu is None:
            raise RuntimeError("Door ECU not set")
        return self._door_ecu.get_dtc()

    @keyword
    def clear_battery_faults(self):
        """Clear all injected battery faults

        Example:
            | Clear Battery Faults |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")

        # Reset cell voltages to nominal
        for i in range(96):
            self._battery_ecu.set_cell_voltage(i, 3.7)
            self._battery_ecu.set_cell_temperature(i, 25.0)

        self._battery_ecu.clear_can_timeout()
        self._battery_ecu.clear_dtc()

        # Clear tracked faults
        self._injected_faults = [
            f
            for f in self._injected_faults
            if f[0]
            not in [
                "cell_overvoltage",
                "cell_undervoltage",
                "cell_overtemperature",
                "cell_undertemperature",
                "low_soc",
                "can_bus_timeout",
            ]
        ]

        logger.info("Cleared all battery faults")

    @keyword
    def clear_door_faults(self):
        """Clear all injected door faults

        Example:
            | Clear Door Faults |
        """
        if self._door_ecu is None:
            raise RuntimeError("Door ECU not set")

        self._door_ecu.set_fault_state(False)
        for door_id in self._door_ecu.doors:
            self._door_ecu.clear_pinch(door_id)

        # Clear tracked faults
        self._injected_faults = [
            f for f in self._injected_faults if f[0] not in ["door_block", "door_ecu_fault"]
        ]

        logger.info("Cleared all door faults")

    @keyword
    def clear_all_faults(self):
        """Clear all injected faults

        Example:
            | Clear All Faults |
        """
        self.clear_battery_faults()
        self.clear_door_faults()
        self._injected_faults = []
        logger.info("Cleared all faults")

    @keyword
    def get_injected_faults(self) -> List[tuple]:
        """
        Get list of all injected faults

        Returns:
            List of (fault_type, parameter) tuples

        Example:
            | ${faults}= | Get Injected Faults |
            | Log | Injected: ${faults} |
        """
        return self._injected_faults.copy()

    @keyword
    def verify_no_battery_faults(self) -> bool:
        """
        Verify no battery faults are present

        Returns:
            True if no faults

        Example:
            | ${clean}= | Verify No Battery Faults |
            | Should Be True | ${clean} |
        """
        if self._battery_ecu is None:
            raise RuntimeError("Battery ECU not set")

        faults = self._battery_ecu.check_faults()
        return len(faults) == 0

    @keyword
    def verify_no_door_faults(self) -> bool:
        """
        Verify no door faults are present

        Returns:
            True if no faults

        Example:
            | ${clean}= | Verify No Door Faults |
            | Should Be True | ${clean} |
        """
        if self._door_ecu is None:
            raise RuntimeError("Door ECU not set")

        faults = self._door_ecu.get_faults()
        return len(faults) == 0


if __name__ == "__main__":
    # Test the library
    from ecu_simulation.battery_ecu import BatteryECU
    from ecu_simulation.door_ecu import DoorECU

    battery = BatteryECU()
    door = DoorECU()

    fault = FaultInjectionLibrary()
    fault.set_battery_ecu(battery)
    fault.set_door_ecu(door)

    print("Testing Fault Injection Library...")

    # Inject and verify battery fault
    fault.inject_cell_overvoltage(0)
    print(f"Fault detected: {fault.verify_battery_fault_detected('OVERVOLTAGE')}")

    # Inject and verify door fault
    fault.inject_door_block(0)
    print(f"Door fault detected: {fault.verify_door_fault_detected(0)}")

    # Clear all
    fault.clear_all_faults()
    print(f"No battery faults: {fault.verify_no_battery_faults()}")

    print("Fault Injection Library test complete")
