"""UDS Diagnostic Server Simulation Module"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Callable

logger = logging.getLogger(__name__)


class SID(Enum):
    """UDS Service IDs"""

    DIAGNOSTIC_SESSION_CONTROL = 0x10
    READ_DATA_BY_IDENTIFIER = 0x22
    READ_MEMORY_BY_ADDRESS = 0x23
    WRITE_DATA_BY_IDENTIFIER = 0x2E
    INPUT_OUTPUT_CONTROL_BY_IDENTIFIER = 0x2F
    ROUTINE_CONTROL = 0x31
    REQUEST_DOWNLOAD = 0x34
    REQUEST_UPLOAD = 0x35
    TRANSFER_DATA = 0x36
    REQUEST_TRANSFER_EXIT = 0x37
    READ_DTC = 0x19
    CLEAR_DTC = 0x14
    SECURITY_ACCESS = 0x27
    COMMUNICATION_CONTROL = 0x28
    AUTHENTICATION = 0x29
    TESTER_PRESENT = 0x3E
    CONTROL_DTC_SETTING = 0x85
    RESPONSE_PENDING = 0x7F


class NRC(Enum):
    """Negative Response Codes"""

    POSITIVE_RESPONSE = 0x00
    GENERAL_REJECT = 0x10
    SERVICE_NOT_SUPPORTED = 0x11
    SUB_FUNCTION_NOT_SUPPORTED = 0x12
    CONDITIONS_NOT_CORRECT = 0x22
    REQUEST_SEQUENCE_ERROR = 0x24
    REQUEST_OUT_OF_RANGE = 0x31
    SECURITY_ACCESS_DENIED = 0x33
    INVALID_KEY = 0x35
    EXCEED_NUMBER_OF_ATTEMPTS = 0x36
    REQUIRED_TIME_DELAY_NOT_EXPIRED = 0x37
    SECURITY_ACCESS_AUTHENTICATION_REQUIRED = 0x6D


class SessionType(Enum):
    """Diagnostic session types"""

    DEFAULT = 0x01
    PROGRAMMING = 0x02
    EXTENDED = 0x03
    SAFETY_SYSTEM = 0x04


@dataclass
class DTCRecord:
    """Diagnostic Trouble Code record"""

    code: str  # e.g., "P0171"
    status: int  # Status byte
    snapshot: Optional[dict] = None


@dataclass
class DiagnosticResponse:
    """Response from diagnostic server"""

    sid: int
    data: bytes
    is_negative: bool = False
    nrc: Optional[int] = None


class DiagnosticServer:
    """
    UDS (ISO 14229) Diagnostic Server implementation.

    Features:
    - Standard UDS service support
    - Multiple session types
    - DTC storage and retrieval
    - Security access
    - Data identifier management
    - Routine execution
    """

    def __init__(self, ecu_name: str = "VirtualECU"):
        """Initialize diagnostic server"""
        self.ecu_name = ecu_name
        self.current_session = SessionType.DEFAULT
        self.security_level = 0
        self.dtcs: Dict[str, DTCRecord] = {}
        self.data_identifiers: Dict[int, bytes] = {}
        self.routines: Dict[int, Callable] = {}
        self.running = False
        self.dtc_setting_enabled = True
        self.tester_present_timeout = 5.0
        self.last_tester_present = 0.0

        # Initialize standard DIDs
        self._initialize_standard_dids()

    def _initialize_standard_dids(self):
        """Initialize standard data identifiers"""
        # Vehicle identification
        self.data_identifiers[0xF10C] = b"Virtual ECU v1.0"  # ECU serial number
        self.data_identifiers[0xF187] = b"VIRTECU"  # Hardware number
        self.data_identifiers[0xF19E] = b"1.0.0"  # Software version
        self.data_identifiers[0xF198] = b"Virtual HIL Framework"  # Supplier

        # Diagnostic data
        self.data_identifiers[0xF10B] = bytes([0x01])  # Session status

    async def process_request(self, request: bytes) -> DiagnosticResponse:
        """
        Process a diagnostic request
        Args:
            request: Raw UDS request bytes
        Returns:
            DiagnosticResponse
        """
        if len(request) < 1:
            return DiagnosticResponse(0x7F, bytes([0x10]), True, 0x10)

        sid = request[0]

        # Reset tester present timer on any valid request
        if sid != SID.TESTER_PRESENT.value:
            self.last_tester_present = asyncio.get_event_loop().time()

        try:
            # Dispatch to appropriate handler
            if sid == SID.DIAGNOSTIC_SESSION_CONTROL.value:
                return await self._handle_session_control(request)
            elif sid == SID.READ_DATA_BY_IDENTIFIER.value:
                return await self._handle_read_did(request)
            elif sid == SID.WRITE_DATA_BY_IDENTIFIER.value:
                return await self._handle_write_did(request)
            elif sid == SID.READ_DTC.value:
                return await self._handle_read_dtc(request)
            elif sid == SID.CLEAR_DTC.value:
                return await self._handle_clear_dtc(request)
            elif sid == SID.SECURITY_ACCESS.value:
                return await self._handle_security_access(request)
            elif sid == SID.ROUTINE_CONTROL.value:
                return await self._handle_routine_control(request)
            elif sid == SID.TESTER_PRESENT.value:
                return await self._handle_tester_present(request)
            elif sid == SID.CONTROL_DTC_SETTING.value:
                return await self._handle_dtc_setting(request)
            else:
                return DiagnosticResponse(
                    0x7F,
                    bytes([sid, NRC.SERVICE_NOT_SUPPORTED.value]),
                    True,
                    NRC.SERVICE_NOT_SUPPORTED.value,
                )
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return DiagnosticResponse(
                0x7F, bytes([sid, NRC.GENERAL_REJECT.value]), True, NRC.GENERAL_REJECT.value
            )

    async def _handle_session_control(self, request: bytes) -> DiagnosticResponse:
        """Handle diagnostic session control (0x10)"""
        if len(request) < 2:
            return DiagnosticResponse(
                0x7F, bytes([0x10, NRC.INVALID_KEY.value]), True, NRC.INVALID_KEY.value
            )

        session_type = request[1]

        try:
            new_session = SessionType(session_type)
            self.current_session = new_session
            logger.info(f"Session changed to {new_session.name}")

            return DiagnosticResponse(
                0x50,  # Positive response SID
                bytes([session_type, 0x00, 0x00]),  # Session type + P2 + P2*
            )
        except ValueError:
            return DiagnosticResponse(
                0x7F,
                bytes([0x10, NRC.SUB_FUNCTION_NOT_SUPPORTED.value]),
                True,
                NRC.SUB_FUNCTION_NOT_SUPPORTED.value,
            )

    async def _handle_read_did(self, request: bytes) -> DiagnosticResponse:
        """Handle read data by identifier (0x22)"""
        if len(request) < 3:
            return DiagnosticResponse(
                0x7F, bytes([0x22, NRC.INVALID_KEY.value]), True, NRC.INVALID_KEY.value
            )

        # Parse DIDs (2 bytes each)
        dids = []
        for i in range(1, len(request), 2):
            if i + 1 < len(request):
                did = (request[i] << 8) | request[i + 1]
                dids.append(did)

        response_data = bytearray()
        for did in dids:
            if did in self.data_identifiers:
                data = self.data_identifiers[did]
                # Add DID and data to response
                response_data.extend(bytes([did >> 8, did & 0xFF]))
                response_data.extend(data)
            else:
                return DiagnosticResponse(
                    0x7F,
                    bytes([0x22, NRC.REQUEST_OUT_OF_RANGE.value]),
                    True,
                    NRC.REQUEST_OUT_OF_RANGE.value,
                )

        return DiagnosticResponse(0x62, bytes(response_data))

    async def _handle_write_did(self, request: bytes) -> DiagnosticResponse:
        """Handle write data by identifier (0x2E)"""
        if len(request) < 3:
            return DiagnosticResponse(
                0x7F, bytes([0x2E, NRC.INVALID_KEY.value]), True, NRC.INVALID_KEY.value
            )

        did = (request[1] << 8) | request[2]
        data = request[3:]

        self.data_identifiers[did] = data
        logger.info(f"Wrote DID 0x{did:04X}: {data.hex()}")

        return DiagnosticResponse(0x6E, bytes([did >> 8, did & 0xFF]))

    async def _handle_read_dtc(self, request: bytes) -> DiagnosticResponse:
        """Handle read DTC (0x19)"""
        if len(request) < 2:
            return DiagnosticResponse(
                0x7F, bytes([0x19, NRC.INVALID_KEY.value]), True, NRC.INVALID_KEY.value
            )

        sub_function = request[1]

        if sub_function == 0x02:  # Read DTC by status
            response_data = bytearray([0x59, 0x02, 0x00])  # Status mask

            for dtc in self.dtcs.values():
                # Convert DTC code to bytes
                code_bytes = self._encode_dtc(dtc.code)
                response_data.extend(code_bytes)
                response_data.append(dtc.status)

            return DiagnosticResponse(0x59, bytes(response_data))

        elif sub_function == 0x0A:  # Read DTC status availability
            return DiagnosticResponse(
                0x59,
                bytes([0x0A, 0x00, 0x00, 0xFF]),  # All DTCs supported
            )

        return DiagnosticResponse(
            0x7F,
            bytes([0x19, NRC.SUB_FUNCTION_NOT_SUPPORTED.value]),
            True,
            NRC.SUB_FUNCTION_NOT_SUPPORTED.value,
        )

    async def _handle_clear_dtc(self, request: bytes) -> DiagnosticResponse:
        """Handle clear DTC (0x14)"""
        if not self.dtc_setting_enabled:
            return DiagnosticResponse(
                0x7F,
                bytes([0x14, NRC.CONDITIONS_NOT_CORRECT.value]),
                True,
                NRC.CONDITIONS_NOT_CORRECT.value,
            )

        # Clear all DTCs
        self.dtcs.clear()
        logger.info("All DTCs cleared")

        return DiagnosticResponse(0x54, bytes([0x00, 0x00]))

    async def _handle_security_access(self, request: bytes) -> DiagnosticResponse:
        """Handle security access (0x27)"""
        if len(request) < 2:
            return DiagnosticResponse(
                0x7F, bytes([0x27, NRC.INVALID_KEY.value]), True, NRC.INVALID_KEY.value
            )

        sub_function = request[1]

        # For simulation, accept any security request
        if sub_function % 2 == 1:  # Request seed
            # Return a dummy seed
            return DiagnosticResponse(0x67, bytes([sub_function, 0x01, 0x02, 0x03, 0x04]))
        else:  # Send key
            self.security_level = sub_function // 2
            return DiagnosticResponse(0x67, bytes([sub_function]))

    async def _handle_routine_control(self, request: bytes) -> DiagnosticResponse:
        """Handle routine control (0x31)"""
        if len(request) < 4:
            return DiagnosticResponse(
                0x7F, bytes([0x31, NRC.INVALID_KEY.value]), True, NRC.INVALID_KEY.value
            )

        control_type = request[1]
        routine_id = (request[2] << 8) | request[3]

        if routine_id in self.routines:
            # Execute registered routine
            try:
                result = await self.routines[routine_id](control_type, request[4:])
                return DiagnosticResponse(
                    0x71, bytes([control_type, routine_id >> 8, routine_id & 0xFF]) + result
                )
            except Exception as e:
                logger.error(f"Routine error: {e}")
                return DiagnosticResponse(
                    0x7F,
                    bytes([0x31, NRC.CONDITIONS_NOT_CORRECT.value]),
                    True,
                    NRC.CONDITIONS_NOT_CORRECT.value,
                )

        return DiagnosticResponse(
            0x7F,
            bytes([0x31, NRC.REQUEST_SEQUENCE_ERROR.value]),
            True,
            NRC.REQUEST_SEQUENCE_ERROR.value,
        )

    async def _handle_tester_present(self, request: bytes) -> DiagnosticResponse:
        """Handle tester present (0x3E)"""
        self.last_tester_present = asyncio.get_event_loop().time()
        # Check for sub-function (suppress response)
        if len(request) > 1 and request[1] == 0x80:
            return DiagnosticResponse(0x00, bytes())  # No response
        return DiagnosticResponse(0x7E, bytes([0x00]))

    async def _handle_dtc_setting(self, request: bytes) -> DiagnosticResponse:
        """Handle control DTC setting (0x85)"""
        if len(request) < 2:
            return DiagnosticResponse(
                0x7F, bytes([0x85, NRC.INVALID_KEY.value]), True, NRC.INVALID_KEY.value
            )

        setting = request[1]
        self.dtc_setting_enabled = bool(setting)
        logger.info(f"DTC setting: {'ON' if self.dtc_setting_enabled else 'OFF'}")

        return DiagnosticResponse(0xC5, bytes([setting]))

    def _encode_dtc(self, code: str) -> bytes:
        """Encode DTC code to bytes"""
        # Parse standard OBD-II format (e.g., "P0171")
        if len(code) < 5:
            return bytes(3)

        system = code[0]
        digits = code[1:]

        # Convert to UDS encoding
        byte0 = 0
        if system == "P":
            byte0 = 0x02
        elif system == "B":
            byte0 = 0x08
        elif system == "C":
            byte0 = 0x01
        elif system == "U":
            byte0 = 0x00

        byte1 = int(digits[0], 16) << 4 | int(digits[1], 16)
        byte2 = int(digits[2], 16) << 4 | int(digits[3], 16)

        return bytes([byte0, byte1, byte2])

    def store_dtc(self, code: str, status: int = 0x01, snapshot: Optional[dict] = None):
        """Store a DTC"""
        self.dtcs[code] = DTCRecord(code=code, status=status, snapshot=snapshot)
        logger.warning(f"DTC stored: {code}")

    def clear_dtc(self, code: str):
        """Clear a specific DTC"""
        if code in self.dtcs:
            del self.dtcs[code]
            logger.info(f"DTC cleared: {code}")

    def get_all_dtcs(self) -> list[DTCRecord]:
        """Get all stored DTCs"""
        return list(self.dtcs.values())

    def register_routine(self, routine_id: int, handler: Callable):
        """Register a routine handler"""
        self.routines[routine_id] = handler

    async def start(self):
        """Start diagnostic server"""
        self.running = True
        self.last_tester_present = asyncio.get_event_loop().time()
        logger.info(f"Diagnostic server started for {self.ecu_name}")

    async def stop(self):
        """Stop diagnostic server"""
        self.running = False
        logger.info(f"Diagnostic server stopped")


if __name__ == "__main__":
    # Quick test
    async def main():
        server = DiagnosticServer()
        await server.start()

        # Test session control
        response = await server.process_request(bytes([0x10, 0x03]))
        print(f"Session response: {response.data.hex()}")

        # Test read DID
        response = await server.process_request(bytes([0x22, 0xF1, 0x0C]))
        print(f"DID response: {response.data}")

        # Store and read DTC
        server.store_dtc("P0171")
        response = await server.process_request(bytes([0x19, 0x02, 0xFF]))
        print(f"DTC response: {response.data.hex()}")

        await server.stop()

    asyncio.run(main())
