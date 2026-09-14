"""Robot Framework HTTP Library for ECU Simulation

This library provides keywords for interacting with virtual ECU simulations
via HTTP REST API, enabling more realistic HIL testing with separate processes.
"""

import logging
from typing import Any, Optional

import requests
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn

logger = logging.getLogger(__name__)


@library
class ECUSimulatorHTTPLibrary:
    """
    Robot Framework HTTP library for ECU simulation control.

    Communicates with the ECU server via HTTP REST API, providing:
    - ECU lifecycle management
    - State queries (SOC, voltage, temperature)
    - Cell-level operations
    - Charging simulation
    - Fault injection and verification

    The library maintains a requests Session for connection pooling.

    Example:
        | *** Settings *** |
        | Library           | ECUSimulatorHTTPLibrary | http://localhost:8000 |
        |                   |                         | timeout=30            |
        |                   |                         | verify=False          |
    """

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_LIBRARY_VERSION = "0.1.0"

    def __init__(
        self, base_url: str = "http://localhost:8000", timeout: float = 30.0, verify: bool = True
    ):
        """
        Initialize the ECU Simulator HTTP Library

        Arguments:
            base_url: Base URL of the ECU server (default: http://localhost:8000)
            timeout: Request timeout in seconds (default: 30.0)
            verify: SSL certificate verification (default: True)

        Example:
            | Library | ECUSimulatorHTTPLibrary | http://ecu-server:8000 |
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify = verify
        self.session = requests.Session()
        self._last_response: Optional[requests.Response] = None
        logger.info(f"Initialized ECUSimulatorHTTPLibrary with base_url={self.base_url}")

    # =============================================================================
    # Helper Methods
    # =============================================================================

    def _url(self, path: str) -> str:
        """Construct full URL from path"""
        return f"{self.base_url}{path}"

    def _handle_response(self, response: requests.Response, error_message: str = "") -> dict:
        """
        Handle HTTP response, raising errors for bad status codes

        Arguments:
            response: The response object
            error_message: Custom error message prefix

        Returns:
            Response JSON as dictionary

        Raises:
            AssertionError: If response indicates an error
        """
        self._last_response = response
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            msg = f"{error_message}: {e}" if error_message else str(e)
            # Try to get error details from response
            try:
                error_details = response.json()
                msg = f"{msg} - Details: {error_details}"
            except Exception:
                if response.text:
                    msg = f"{msg} - Response: {response.text[:200]}"
            raise AssertionError(msg) from e

        # Return JSON for successful responses
        if response.status_code == 204:  # No Content
            return {}
        return response.json()

    def _get(self, path: str, error_message: str = "") -> dict:
        """Perform GET request"""
        url = self._url(path)
        logger.debug(f"GET {url}")
        response = self.session.get(url, timeout=self.timeout, verify=self.verify)
        return self._handle_response(response, error_message)

    def _post(self, path: str, data: Optional[dict] = None, error_message: str = "") -> dict:
        """Perform POST request"""
        url = self._url(path)
        logger.debug(f"POST {url} data={data}")
        response = self.session.post(
            url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
            verify=self.verify,
        )
        return self._handle_response(response, error_message)

    def _delete(self, path: str, data: Optional[dict] = None, error_message: str = "") -> dict:
        """Perform DELETE request"""
        url = self._url(path)
        logger.debug(f"DELETE {url} data={data}")
        response = self.session.delete(
            url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
            verify=self.verify,
        )
        return self._handle_response(response, error_message)

    def _put(self, path: str, data: Optional[dict] = None, error_message: str = "") -> dict:
        """Perform PUT request"""
        url = self._url(path)
        logger.debug(f"PUT {url} data={data}")
        response = self.session.put(
            url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
            verify=self.verify,
        )
        return self._handle_response(response, error_message)

    # =============================================================================
    # ECU Control Keywords
    # =============================================================================

    @keyword
    def start_ecu(self) -> str:
        """
        Start the ECU simulation via HTTP API

        Returns:
            Confirmation message

        Example:
            | ${result}= | Start ECU |
            | Should Contain | ${result} | started |
        """
        result = self._post("/ecu/start", "Failed to start ECU")
        logger.info("ECU started")
        return result.get("message", "ECU started")

    @keyword
    def stop_ecu(self) -> str:
        """
        Stop the ECU simulation via HTTP API

        Returns:
            Confirmation message

        Example:
            | ${result}= | Stop ECU |
        """
        result = self._post("/ecu/stop", "Failed to stop ECU")
        logger.info("ECU stopped")
        return result.get("message", "ECU stopped")

    @keyword
    def get_ecu_status(self) -> dict:
        """
        Get full ECU status

        Returns:
            Dictionary with complete ECU state

        Example:
            | ${status}= | Get ECU Status |
            | Log | SOC: ${status}[soc]% |
        """
        result = self._get("/ecu/status", "Failed to get ECU status")
        logger.debug(f"ECU status: {result}")
        return result

    # =============================================================================
    # State Query Keywords
    # =============================================================================

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
        result = self._get("/ecu/state/soc", "Failed to get battery SOC")
        return float(result["value"])

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
        result = self._get("/ecu/state/voltage", "Failed to get battery voltage")
        return float(result["value"])

    @keyword
    def get_battery_current(self) -> float:
        """
        Get the current pack current from battery ECU

        Returns:
            Current in Amps

        Example:
            | ${current}= | Get Battery Current |
        """
        result = self._get("/ecu/state/current", "Failed to get battery current")
        return float(result["value"])

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
        result = self._get("/ecu/state/temperature", "Failed to get battery temperature")
        return float(result["value"])

    @keyword
    def get_battery_soh(self) -> float:
        """
        Get the State of Health (SOH) from battery ECU

        Returns:
            SOH percentage (0-100)

        Example:
            | ${soh}= | Get Battery SOH |
        """
        result = self._get("/ecu/state/soh", "Failed to get battery SOH")
        return float(result["value"])

    # =============================================================================
    # Cell Management Keywords
    # =============================================================================

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
        result = self._get(f"/ecu/cell/{cell_id}/voltage", "Failed to get cell voltage")
        return float(result["voltage"])

    @keyword
    def set_cell_voltage(self, cell_id: int, voltage: float) -> str:
        """
        Set voltage of a specific cell (for fault injection)

        Arguments:
            cell_id: Cell identifier
            voltage: New voltage value in Volts

        Returns:
            Confirmation message

        Example:
            | Set Cell Voltage | cell_id=0 | voltage=5.0 |
        """
        result = self._put(
            f"/ecu/cell/{cell_id}/voltage",
            {"voltage": voltage},
            f"Failed to set cell {cell_id} voltage",
        )
        logger.info(f"Set cell {cell_id} voltage to {voltage}V")
        return result.get("message", f"Cell {cell_id} voltage set")

    @keyword
    def get_cell_temperature(self, cell_id: int) -> float:
        """
        Get temperature of a specific battery cell

        Arguments:
            cell_id: Cell identifier

        Returns:
            Cell temperature in Celsius

        Example:
            | ${temp}= | Get Cell Temperature | cell_id=0 |
        """
        result = self._get(f"/ecu/cell/{cell_id}/temperature", "Failed to get cell temperature")
        return float(result["temperature"])

    @keyword
    def set_cell_temperature(self, cell_id: int, temperature: float) -> str:
        """
        Set temperature of a specific cell (for fault injection)

        Arguments:
            cell_id: Cell identifier
            temperature: New temperature value in Celsius

        Returns:
            Confirmation message

        Example:
            | Set Cell Temperature | cell_id=0 | temperature=80 |
        """
        result = self._put(
            f"/ecu/cell/{cell_id}/temperature",
            {"temperature": temperature},
            f"Failed to set cell {cell_id} temperature",
        )
        logger.info(f"Set cell {cell_id} temperature to {temperature}C")
        return result.get("message", f"Cell {cell_id} temperature set")

    # =============================================================================
    # Simulation Control Keywords
    # =============================================================================

    @keyword
    def simulate_charging(self, current: float, duration: float) -> dict:
        """
        Simulate battery charging or discharging

        Arguments:
            current: Current in Amps (positive = charging, negative = discharging)
            duration: Duration in seconds

        Returns:
            Dictionary with charging results including new SOC

        Example:
            | ${result}= | Simulate Charging | current=10 | duration=60 |
            | Log | SOC changed from ${result}[details][old_soc]% to ${result}[details][new_soc]% |
        """
        result = self._post(
            "/ecu/charge", {"current": current, "duration": duration}, "Failed to simulate charging"
        )
        logger.info(f"Simulated charging: {current}A for {duration}s")
        return result

    @keyword
    def balance_cells(self) -> str:
        """
        Trigger cell balancing in battery ECU

        Returns:
            Confirmation message

        Example:
            | Balance Cells |
        """
        result = self._post("/ecu/balance", "Failed to balance cells")
        logger.info("Cell balancing triggered")
        return result.get("message", "Cell balancing completed")

    # =============================================================================
    # Fault Management Keywords
    # =============================================================================

    @keyword
    def get_active_faults(self) -> list:
        """
        Get active faults from the ECU

        Returns:
            List of active fault codes

        Example:
            | ${faults}= | Get Active Faults |
            | Log | Active faults: ${faults} |
        """
        result = self._get("/ecu/faults", "Failed to get faults")
        return result.get("faults", [])

    @keyword
    def get_dtc(self) -> Optional[str]:
        """
        Get Diagnostic Trouble Code (DTC) if any

        Returns:
            DTC string or None if no fault

        Example:
            | ${dtc}= | Get DTC |
            | Log | DTC: ${dtc} |
        """
        result = self._get("/ecu/faults", "Failed to get DTC")
        return result.get("dtc")

    @keyword
    def clear_dtc(self) -> str:
        """
        Clear stored Diagnostic Trouble Codes

        Returns:
            Confirmation message

        Example:
            | Clear DTC |
        """
        result = self._post("/ecu/dtc/clear", "Failed to clear DTC")
        logger.info("DTCs cleared")
        return result.get("message", "DTCs cleared")

    @keyword
    def inject_can_bus_timeout(self) -> str:
        """
        Inject a CAN bus timeout fault

        Returns:
            Confirmation message

        Example:
            | Inject CAN Bus Timeout |
        """
        result = self._post("/ecu/fault/can_timeout", "Failed to inject CAN bus timeout")
        logger.info("CAN bus timeout injected")
        return result.get("message", "CAN bus timeout injected")

    @keyword
    def clear_can_bus_timeout(self) -> str:
        """
        Clear a CAN bus timeout fault

        Returns:
            Confirmation message

        Example:
            | Clear CAN Bus Timeout |
        """
        result = self._delete(
            "/ecu/fault/can_timeout", error_message="Failed to clear CAN bus timeout"
        )
        logger.info("CAN bus timeout cleared")
        return result.get("message", "CAN bus timeout cleared")

    @keyword
    def ecu_should_have_fault(self, fault_code: str):
        """
        Verify that a specific fault is active

        Arguments:
            fault_code: Expected fault code (e.g., "OVERVOLTAGE")

        Example:
            | ECU Should Have Fault | OVERVOLTAGE |
        """
        faults = self.get_active_faults()
        if fault_code not in faults:
            raise AssertionError(
                f"Expected fault '{fault_code}' not found. Active faults: {faults}"
            )

    @keyword
    def ecu_should_have_no_faults(self):
        """
        Verify that no faults are active

        Example:
            | ECU Should Have No Faults |
        """
        faults = self.get_active_faults()
        if faults:
            raise AssertionError(f"Expected no faults, but found: {faults}")

    # =============================================================================
    # System Keywords
    # =============================================================================

    @keyword
    def check_ecu_health(self) -> str:
        """
        Check if ECU server is healthy

        Returns:
            Health status string

        Raises:
            AssertionError: If health check fails

        Example:
            | ${status}= | Check ECU Health |
            | Should Be Equal | ${status} | healthy |
        """
        result = self._get("/health", "ECU health check failed")
        return result.get("status", "unknown")

    @keyword
    def wait_for_ecu_ready(self, timeout: float = 30.0, interval: float = 0.5) -> bool:
        """
        Wait for ECU server to be ready (accepts both 'healthy' and 'stopped' states)

        Arguments:
            timeout: Maximum time to wait in seconds
            interval: Time between checks in seconds

        Returns:
            True if ECU is ready, False if timeout

        Example:
            | ${ready}= | Wait For ECU Ready | timeout=10 |
            | Should Be True | ${ready} |
        """
        import time

        end_time = time.time() + timeout

        while time.time() < end_time:
            try:
                result = self._get("/health", "ECU health check failed")
                status = result.get("status", "unknown")
                logger.info(f"Health check result: {result}, status={status}")
                # Accept both 'healthy' and 'stopped' as valid states
                # The ECU can be started later via Start ECU
                if status in ("healthy", "stopped"):
                    logger.info(f"ECU server is ready (status: {status})")
                    return True
            except Exception as e:
                logger.debug(f"Health check failed: {e}")

            time.sleep(interval)

        logger.error(f"ECU not ready after {timeout}s")
        return False

    @keyword
    def get_last_response_info(self) -> dict:
        """
        Get information about the last HTTP response

        Returns:
            Dictionary with status_code, url, and headers

        Example:
            | ${info}= | Get Last Response Info |
            | Log | Last request: ${info}[url] returned ${info}[status_code] |
        """
        if self._last_response is None:
            return {}

        return {
            "status_code": self._last_response.status_code,
            "url": self._last_response.url,
            "headers": dict(self._last_response.headers),
        }


if __name__ == "__main__":
    # Test the library
    lib = ECUSimulatorHTTPLibrary()

    print("Testing ECU Simulator HTTP Library...")

    # Health check
    print(f"Health: {lib.check_ecu_health()}")

    # Get status
    status = lib.get_ecu_status()
    print(f"SOC: {status['soc']}%")
    print(f"Voltage: {status['voltage']}V")

    # Get individual values
    print(f"SOC: {lib.get_battery_soc()}%")
    print(f"Voltage: {lib.get_battery_voltage()}V")
    print(f"Temperature: {lib.get_battery_temperature()}C")

    # Check faults
    print(f"Active faults: {lib.get_active_faults()}")

    print("Library test complete")
