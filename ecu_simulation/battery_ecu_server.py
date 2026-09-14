"""FastAPI-based HTTP server for Battery ECU simulation

This module provides a REST API interface to the Battery ECU simulation,
enabling HTTP-based HIL testing with separate processes for more realistic testing.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from ecu_simulation.battery_ecu import BatteryECU

logger = logging.getLogger(__name__)

# Global ECU instance
ecu_instance: Optional[BatteryECU] = None


# =============================================================================
# Pydantic Models for Request/Response Validation
# =============================================================================


class ChargeRequest(BaseModel):
    """Request model for charging simulation"""

    current: float = Field(..., description="Charging current in Amps (positive = charging)")
    duration: float = Field(..., description="Duration in seconds", ge=0)

    @field_validator("current")
    @classmethod
    def validate_current(cls, v: float) -> float:
        """Validate current is within reasonable bounds"""
        if not -500 <= v <= 500:
            raise ValueError("Current must be between -500 and 500 Amps")
        return v


class CellVoltageRequest(BaseModel):
    """Request model for setting cell voltage (fault injection)"""

    voltage: float = Field(..., description="Cell voltage in Volts")

    @field_validator("voltage")
    @classmethod
    def validate_voltage(cls, v: float) -> float:
        """Validate voltage is within physical limits"""
        if not 0 <= v <= 10:
            raise ValueError("Voltage must be between 0 and 10 Volts")
        return v


class CellTemperatureRequest(BaseModel):
    """Request model for setting cell temperature (fault injection)"""

    temperature: float = Field(..., description="Cell temperature in Celsius")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is within physical limits"""
        if not -50 <= v <= 150:
            raise ValueError("Temperature must be between -50 and 150 Celsius")
        return v


class ECUStatusResponse(BaseModel):
    """Response model for ECU status"""

    soc: float = Field(..., description="State of Charge (%)")
    soh: float = Field(..., description="State of Health (%)")
    voltage: float = Field(..., description="Pack voltage (V)")
    current: float = Field(..., description="Pack current (A)")
    temperature: float = Field(..., description="Average pack temperature (C)")
    max_cell_temp: float = Field(..., description="Maximum cell temperature (C)")
    min_cell_temp: float = Field(..., description="Minimum cell temperature (C)")
    max_cell_voltage: float = Field(..., description="Maximum cell voltage (V)")
    min_cell_voltage: float = Field(..., description="Minimum cell voltage (V)")
    can_timeout: bool = Field(..., description="CAN bus timeout fault status")
    faults: List[str] = Field(default_factory=list, description="Active fault codes")
    running: bool = Field(..., description="ECU running status")


class StateResponse(BaseModel):
    """Response model for individual state queries"""

    value: float


class CellVoltageResponse(BaseModel):
    """Response model for cell voltage queries"""

    cell_id: int
    voltage: float


class CellTemperatureResponse(BaseModel):
    """Response model for cell temperature queries"""

    cell_id: int
    temperature: float


class FaultsResponse(BaseModel):
    """Response model for faults query"""

    faults: List[str] = Field(default_factory=list, description="Active fault codes")
    dtc: Optional[str] = Field(None, description="Diagnostic Trouble Code")


class HealthResponse(BaseModel):
    """Response model for health check"""

    status: str
    version: str = "0.1.0"


class SuccessResponse(BaseModel):
    """Generic success response"""

    message: str
    details: Optional[Dict] = None


# =============================================================================
# Lifespan Management
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - initialize and cleanup ECU"""
    global ecu_instance

    # Startup
    logger.info("Starting Battery ECU API server")
    ecu_instance = BatteryECU()
    await ecu_instance.start()
    logger.info("Battery ECU initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down Battery ECU API server")
    if ecu_instance:
        await ecu_instance.stop()
        ecu_instance = None
    logger.info("Battery ECU API server stopped")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Battery ECU Server",
    description="REST API for Battery ECU simulation in HIL testing",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# Helper Functions
# =============================================================================


def get_ecu() -> BatteryECU:
    """Get the global ECU instance"""
    if ecu_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ECU not initialized"
        )
    return ecu_instance


def validate_cell_id(cell_id: int) -> None:
    """Validate cell ID exists"""
    ecu = get_ecu()
    if cell_id not in ecu.cells:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cell {cell_id} not found. Valid range: 0-{len(ecu.cells) - 1}",
        )


# =============================================================================
# ECU Control Endpoints
# =============================================================================


@app.post("/ecu/start", response_model=SuccessResponse, tags=["ECU Control"])
async def start_ecu() -> SuccessResponse:
    """
    Start the ECU simulation

    Returns confirmation that the ECU has been started.
    """
    ecu = get_ecu()
    await ecu.start()
    logger.info("ECU started via API")
    return SuccessResponse(message="ECU started successfully")


@app.post("/ecu/stop", response_model=SuccessResponse, tags=["ECU Control"])
async def stop_ecu() -> SuccessResponse:
    """
    Stop the ECU simulation

    Returns confirmation that the ECU has been stopped.
    """
    ecu = get_ecu()
    await ecu.stop()
    logger.info("ECU stopped via API")
    return SuccessResponse(message="ECU stopped successfully")


@app.get("/ecu/status", response_model=ECUStatusResponse, tags=["ECU Control"])
async def get_ecu_status() -> ECUStatusResponse:
    """
    Get full ECU state

    Returns complete status of the battery ECU including all state variables.
    """
    ecu = get_ecu()
    status_dict = ecu.to_dict()
    status_dict["running"] = ecu.running
    return ECUStatusResponse(**status_dict)


# =============================================================================
# State Query Endpoints
# =============================================================================


@app.get("/ecu/state/soc", response_model=StateResponse, tags=["State"])
async def get_soc() -> StateResponse:
    """Get State of Charge (SOC) percentage"""
    ecu = get_ecu()
    return StateResponse(value=ecu.get_soc())


@app.get("/ecu/state/voltage", response_model=StateResponse, tags=["State"])
async def get_voltage() -> StateResponse:
    """Get pack voltage in Volts"""
    ecu = get_ecu()
    return StateResponse(value=ecu.get_pack_voltage())


@app.get("/ecu/state/current", response_model=StateResponse, tags=["State"])
async def get_current() -> StateResponse:
    """Get pack current in Amps"""
    ecu = get_ecu()
    return StateResponse(value=ecu.get_pack_current())


@app.get("/ecu/state/temperature", response_model=StateResponse, tags=["State"])
async def get_temperature() -> StateResponse:
    """Get average pack temperature in Celsius"""
    ecu = get_ecu()
    return StateResponse(value=ecu.get_pack_temperature())


@app.get("/ecu/state/soh", response_model=StateResponse, tags=["State"])
async def get_soh() -> StateResponse:
    """Get State of Health (SOH) percentage"""
    ecu = get_ecu()
    return StateResponse(value=ecu.get_soh())


# =============================================================================
# Cell Management Endpoints
# =============================================================================


@app.get(
    "/ecu/cell/{cell_id}/voltage", response_model=CellVoltageResponse, tags=["Cell Management"]
)
async def get_cell_voltage(cell_id: int) -> CellVoltageResponse:
    """
    Get voltage of a specific cell

    - **cell_id**: Cell identifier (0-based index)
    """
    validate_cell_id(cell_id)
    ecu = get_ecu()
    voltage = ecu.get_cell_voltage(cell_id)
    return CellVoltageResponse(cell_id=cell_id, voltage=voltage)


@app.put("/ecu/cell/{cell_id}/voltage", response_model=SuccessResponse, tags=["Cell Management"])
async def set_cell_voltage(cell_id: int, request: CellVoltageRequest) -> SuccessResponse:
    """
    Set voltage of a specific cell (for fault injection)

    - **cell_id**: Cell identifier (0-based index)
    - **voltage**: New voltage value in Volts
    """
    validate_cell_id(cell_id)
    ecu = get_ecu()
    ecu.set_cell_voltage(cell_id, request.voltage)
    logger.info(f"Set cell {cell_id} voltage to {request.voltage}V")
    return SuccessResponse(
        message=f"Cell {cell_id} voltage set",
        details={"cell_id": cell_id, "voltage": request.voltage},
    )


@app.get(
    "/ecu/cell/{cell_id}/temperature",
    response_model=CellTemperatureResponse,
    tags=["Cell Management"],
)
async def get_cell_temperature(cell_id: int) -> CellTemperatureResponse:
    """
    Get temperature of a specific cell

    - **cell_id**: Cell identifier (0-based index)
    """
    validate_cell_id(cell_id)
    ecu = get_ecu()
    temperature = ecu.get_cell_temperature(cell_id)
    return CellTemperatureResponse(cell_id=cell_id, temperature=temperature)


@app.put(
    "/ecu/cell/{cell_id}/temperature", response_model=SuccessResponse, tags=["Cell Management"]
)
async def set_cell_temperature(cell_id: int, request: CellTemperatureRequest) -> SuccessResponse:
    """
    Set temperature of a specific cell (for fault injection)

    - **cell_id**: Cell identifier (0-based index)
    - **temperature**: New temperature value in Celsius
    """
    validate_cell_id(cell_id)
    ecu = get_ecu()
    ecu.set_cell_temperature(cell_id, request.temperature)
    logger.info(f"Set cell {cell_id} temperature to {request.temperature}C")
    return SuccessResponse(
        message=f"Cell {cell_id} temperature set",
        details={"cell_id": cell_id, "temperature": request.temperature},
    )


# =============================================================================
# Simulation Control Endpoints
# =============================================================================


@app.post("/ecu/charge", response_model=SuccessResponse, tags=["Simulation"])
async def simulate_charge(request: ChargeRequest) -> SuccessResponse:
    """
    Simulate battery charging or discharging

    - **current**: Current in Amps (positive = charging, negative = discharging)
    - **duration**: Duration in seconds

    Returns the new SOC after charging.
    """
    ecu = get_ecu()
    old_soc = ecu.get_soc()
    ecu.simulate_charge(request.current, request.duration)
    new_soc = ecu.get_soc()
    logger.info(
        f"Charging: {request.current}A for {request.duration}s, SOC: {old_soc}% -> {new_soc}%"
    )
    return SuccessResponse(
        message="Charge simulation completed",
        details={
            "current": request.current,
            "duration": request.duration,
            "old_soc": old_soc,
            "new_soc": new_soc,
            "soc_change": new_soc - old_soc,
        },
    )


@app.post("/ecu/balance", response_model=SuccessResponse, tags=["Simulation"])
async def balance_cells() -> SuccessResponse:
    """
    Trigger cell balancing

    Equalizes cell voltages by moving them toward the average.
    """
    ecu = get_ecu()
    ecu.balance_cells()
    logger.info("Cell balancing triggered")
    return SuccessResponse(message="Cell balancing completed")


# =============================================================================
# Fault Management Endpoints
# =============================================================================


@app.get("/ecu/faults", response_model=FaultsResponse, tags=["Faults"])
async def get_faults() -> FaultsResponse:
    """
    Get active faults and Diagnostic Trouble Code (DTC)

    Returns all active fault codes and the current DTC if any.
    """
    ecu = get_ecu()
    faults = ecu.check_faults()
    dtc = ecu.get_dtc()
    return FaultsResponse(faults=faults, dtc=dtc)


@app.post("/ecu/dtc/clear", response_model=SuccessResponse, tags=["Faults"])
async def clear_dtc() -> SuccessResponse:
    """
    Clear stored Diagnostic Trouble Codes (DTCs)

    Clears any stored fault codes in the ECU.
    """
    ecu = get_ecu()
    ecu.clear_dtc()
    logger.info("DTCs cleared")
    return SuccessResponse(message="DTCs cleared successfully")


@app.post("/ecu/fault/can_timeout", response_model=SuccessResponse, tags=["Faults"])
async def inject_can_timeout() -> SuccessResponse:
    """Inject a CAN bus timeout fault."""
    ecu = get_ecu()
    ecu.inject_can_timeout()
    logger.info("CAN bus timeout injected")
    return SuccessResponse(message="CAN bus timeout injected successfully")


@app.delete("/ecu/fault/can_timeout", response_model=SuccessResponse, tags=["Faults"])
async def clear_can_timeout() -> SuccessResponse:
    """Clear a CAN bus timeout fault."""
    ecu = get_ecu()
    ecu.clear_can_timeout()
    logger.info("CAN bus timeout cleared")
    return SuccessResponse(message="CAN bus timeout cleared successfully")


# =============================================================================
# System Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint for CI/CD and monitoring

    Returns server health status and version.
    """
    ecu = get_ecu()
    return HealthResponse(status="healthy" if ecu.running else "stopped", version="0.1.0")


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run the FastAPI server"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    uvicorn.run(
        "ecu_simulation.battery_ecu_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
