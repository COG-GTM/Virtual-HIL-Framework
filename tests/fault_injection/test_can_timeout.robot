*** Settings ***
Documentation     CAN bus timeout fault injection tests

Resource          ../../resources/common_keywords.robot
Resource          ../../resources/ecu_variables.robot
Library           libraries.ECUSimulatorLibrary
Library           libraries.FaultInjectionLibrary
Library           Collections

Suite Setup       Start Fault Injection Environment
Suite Teardown    Clear Battery Faults And Stop Simulations
Test Teardown     Clear Battery Faults
Test Timeout      30 seconds


*** Test Cases ***
Battery ECU Has No CAN Timeout Fault At Startup
    [Tags]    fault_injection    can    battery    smoke

    ${clean}=    Verify No Battery Faults
    Should Be True    ${clean}


Inject CAN Bus Timeout Fault
    [Tags]    fault_injection    can    battery    critical

    Inject CAN Bus Timeout
    ${detected}=    Verify Battery Fault Detected    fault_name=CAN_TIMEOUT
    Should Be True    ${detected}
    ${dtc}=    Get Battery DTC
    Should Be Equal    ${dtc}    BMS_CAN_TIMEOUT_ACTIVE
    ${faults}=    Get Injected Faults
    Log    Injected faults: ${faults}


Clear CAN Bus Timeout Fault Restores Communication
    [Tags]    fault_injection    can    battery

    Inject CAN Bus Timeout
    Verify Battery Fault Detected    fault_name=CAN_TIMEOUT
    Clear CAN Bus Timeout
    ${clean}=    Verify No Battery Faults
    Should Be True    ${clean}
    ${dtc}=    Get Battery DTC
    Should Be Equal    ${dtc}    ${None}


CAN Timeout Does Not Affect Battery State Readings
    [Tags]    fault_injection    can    battery

    ${soc_before}=    Get Battery SOC
    ${voltage_before}=    Get Battery Voltage
    Inject CAN Bus Timeout
    ${soc_after}=    Get Battery SOC
    ${voltage_after}=    Get Battery Voltage
    Should Be Equal As Numbers    ${soc_before}    ${soc_after}
    Should Be Equal As Numbers    ${voltage_before}    ${voltage_after}
    ${detected}=    Verify Battery Fault Detected    fault_name=CAN_TIMEOUT
    Should Be True    ${detected}


*** Keywords ***
Start Fault Injection Environment
    Start Battery Simulation    num_cells=${NUM_CELLS}
    ${ecu}=    Get Battery ECU Instance
    Set Battery ECU    ${ecu}

Clear Battery Faults And Stop Simulations
    Clear Battery Faults
    Stop All Simulations
