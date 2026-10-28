*** Settings ***
Documentation     ECU-specific variables and constants
...               This file contains all ECU configuration values and test limits.


*** Variables ***
# =============================================================================
# Battery ECU Configuration
# =============================================================================

# Battery pack configuration
${NUM_CELLS}             96
${CELL_CAPACITY}         3.2    # Ah
${PACK_CAPACITY}         307.2  # Ah (96 * 3.2)
${NOMINAL_VOLTAGE}       3.7    # V per cell
${PACK_VOLTAGE}          355.2  # V (96 * 3.7)

# Voltage limits
${MAX_CELL_VOLTAGE}      4.2    # V
${MIN_CELL_VOLTAGE}      2.8    # V
${MAX_PACK_VOLTAGE}      403.2  # V
${MIN_PACK_VOLTAGE}      268.8  # V

# Temperature limits (Celsius)
${MAX_CELL_TEMP}         ${60.0}
${MIN_CELL_TEMP}         ${-20.0}
${MAX_OPERATING_TEMP}    ${45.0}
${MIN_OPERATING_TEMP}    ${-10.0}

# SOC limits
${MAX_SOC}               100.0  # %
${MIN_SOC}               0.0    # %
${WARNING_SOC_LOW}       10.0   # %
${WARNING_SOC_HIGH}      90.0   # %

# Current limits
${MAX_CHARGE_CURRENT}    50.0   # A
${MAX_DISCHARGE_CURRENT}    -100.0 # A

# =============================================================================
# Door ECU Configuration
# =============================================================================

# Door configuration
${NUM_DOORS}             4
${DOOR_FL}               0
${DOOR_FR}               1
${DOOR_RL}               2
${DOOR_RR}               3

# Door position states
${DOOR_CLOSED}           CLOSED
${DOOR_OPEN}             OPEN
${DOOR_OPENING}          OPENING
${DOOR_CLOSING}          CLOSING
${DOOR_BLOCKED}          BLOCKED
${DOOR_FAULT}            FAULT

# Lock states
${LOCK_LOCKED}           LOCKED
${LOCK_UNLOCKED}         UNLOCKED
${LOCK_CHILD_LOCKED}     CHILD_LOCKED

# Window limits
${MAX_WINDOW_POSITION}   100.0  # %
${MIN_WINDOW_POSITION}   0.0    # %

# =============================================================================
# CAN Configuration
# =============================================================================

# CAN message IDs
${CAN_BMS_STATUS_ID}     0x100
${CAN_BMS_CELL_DATA_ID}  0x101
${CAN_BMS_FAULT_ID}      0x102
${CAN_BDC_STATUS_ID}     0x200
${CAN_BDC_DOOR_POS_ID}   0x201
${CAN_BDC_LOCK_STATUS_ID}    0x202

# CAN bus settings
${CAN_CHANNEL}           virtual0
${CAN_BITRATE}           500000
${CAN_MAX_BUS_LOAD}      80.0   # %

# =============================================================================
# Diagnostic Configuration
# =============================================================================

# UDS Session types
${SESSION_DEFAULT}       0x01
${SESSION_PROGRAMMING}   0x02
${SESSION_EXTENDED}      0x03
${SESSION_SAFETY}        0x04

# UDS Service IDs
${SID_SESSION_CONTROL}   0x10
${SID_READ_DID}          0x22
${SID_WRITE_DID}         0x2E
${SID_READ_DTC}          0x19
${SID_CLEAR_DTC}         0x14
${SID_SECURITY_ACCESS}   0x27
${SID_ROUTINE_CONTROL}   0x31
${SID_TESTER_PRESENT}    0x3E

# Standard DIDs
${DID_ECU_SERIAL}        0xF10C
${DID_HARDWARE_NUMBER}   0xF187
${DID_SOFTWARE_VERSION}  0xF19E
${DID_SUPPLIER}          0xF198

# DTC masks
${DTC_STATUS_MASK_ALL}   0xFF
${DTC_STATUS_MASK_TEST_FAILED}     0x01
${DTC_STATUS_MASK_TEST_FAILED_THIS_OPERATION_CYCLE}     0x02
${DTC_STATUS_MASK_PENDING}     0x04
${DTC_STATUS_MASK_CONFIRMED}     0x08

# =============================================================================
# Fault Injection Configuration
# =============================================================================

# Fault types
${FAULT_OVERVOLTAGE}     OVERVOLTAGE
${FAULT_UNDERVOLTAGE}    UNDERVOLTAGE
${FAULT_OVERTEMPERATURE}     OVERTEMPERATURE
${FAULT_UNDERTEMPERATURE}     UNDERTEMPERATURE
${FAULT_LOW_SOC}         LOW_SOC
${FAULT_DOOR_BLOCK}      DOOR_BLOCK
${FAULT_DOOR_ECU}        DOOR_ECU_FAULT
${FAULT_CAN_BUS_OFF}     CAN_BUS_OFF

# Fault injection delays
${FAULT_DETECTION_DELAY}     0.5    # s
${FAULT_CLEARANCE_DELAY}     1.0    # s

# =============================================================================
# Test Timing Configuration
# =============================================================================

# Default timeouts
${TIMEOUT_SHORT}         5s
${TIMEOUT_DEFAULT}       10s
${TIMEOUT_LONG}          30s
${TIMEOUT_VERY_LONG}     60s

# Delays
${DELAY_SHORT}           0.1s
${DELAY_DEFAULT}         0.5s
${DELAY_LONG}            1.0s

# =============================================================================
# Test Data Ranges
# =============================================================================

# Valid SOC range for testing
${TEST_SOC_MIN}          20
${TEST_SOC_MAX}          80

# Valid voltage range for testing (per cell)
${TEST_VOLTAGE_MIN}      3.2
${TEST_VOLTAGE_MAX}      4.1

# Valid temperature range for testing
${TEST_TEMP_MIN}         15
${TEST_TEMP_MAX}         35

# =============================================================================
# Expected Values
# =============================================================================

# Expected precision tolerances
${VOLTAGE_TOLERANCE}     0.05   # V
${TEMP_TOLERANCE}        1.0    # C
${SOC_TOLERANCE}         0.5    # %

# Expected cell balance spread
${MAX_CELL_SPREAD}       0.1    # V (when balanced)
${ACCEPTABLE_SPREAD}     0.3    # V (normal operation)

# =============================================================================
# Performance Thresholds
# =============================================================================

# Maximum response times
${MAX_RESPONSE_TIME}     100    # ms for state query
${MAX_CAN_TX_TIME}       10     # ms
${MAX_DIAG_RESPONSE_TIME}     500   # ms

# Minimum throughput
${MIN_MSG_PER_SECOND}    100    # CAN messages


*** Variables ***    # Lists and dictionaries

# Door names mapping
&{DOOR_NAMES}          FL=Front Left    FR=Front Right
...                    RL=Rear Left     RR=Rear Right

# Test door IDs
@{TEST_DOOR_IDS}       0    1    2    3

# Test cell IDs (sample cells for testing)
@{TEST_CELL_IDS}       0    10    50    95
