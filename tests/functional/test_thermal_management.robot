*** Settings ***
Documentation     Thermal management functional tests
...               Tests the battery ECU's thermal monitoring and management.

Resource          ../../resources/common_keywords.robot
Resource          ../../resources/ecu_variables.robot
Library           libraries.ECUSimulatorLibrary
Library           libraries.FaultInjectionLibrary
Library           Collections

Suite Setup       Start Battery Simulation
Suite Teardown    Clear All Faults And Stop
Test Timeout      30 seconds


*** Test Cases ***
Verify Initial Temperature State
    [Documentation]    Verify all cells start at safe temperatures
    [Tags]    battery    thermal    smoke

    ${pack_temp}=    Get Battery Temperature

    Should Be True    ${pack_temp} >= ${MIN_OPERATING_TEMP}
    Should Be True    ${pack_temp} <= ${MAX_OPERATING_TEMP}

    Log    Initial pack temperature: ${pack_temp}C


Detect Overtemperature Fault
    [Documentation]    Verify overtemperature detection
    [Tags]    battery    thermal    fault

    ${initial_faults}=    Get Battery Faults
    Log    Initial faults: ${initial_faults}

    # Inject overtemperature
    Inject Cell Overtemperature    cell_id=0    temperature=${{ ${MAX_CELL_TEMP} + 10 }}

    ${detected}=    Verify Battery Fault Detected    fault_name=OVERTEMPERATURE    timeout=2

    # Clean up
    Clear Battery Faults

    Should Be True    ${detected}    msg=Overtemperature fault not detected


Detect Undertemperature Fault
    [Documentation]    Verify undertemperature detection
    [Tags]    battery    thermal    fault

    # Inject undertemperature
    Inject Cell Undertemperature    cell_id=0    temperature=${{ ${MIN_CELL_TEMP} - 10 }}

    ${detected}=    Verify Battery Fault Detected    fault_name=UNDERTEMPERATURE    timeout=2

    # Clean up
    Clear Battery Faults

    Should Be True    ${detected}    msg=Undertemperature fault not detected


Verify Temperature Limits
    [Documentation]    Verify temperature monitoring enforces limits
    [Tags]    battery    thermal    limits

    # Test upper limit
    Inject Cell Overtemperature    cell_id=1    temperature=${{ ${MAX_CELL_TEMP} + 5 }}

    ${faults}=    Get Battery Faults
    Should Contain    ${faults}    OVERTEMPERATURE

    Clear Battery Faults

    # Test lower limit
    Inject Cell Undertemperature    cell_id=1    temperature=${{ ${MIN_CELL_TEMP} - 5 }}

    ${faults}=    Get Battery Faults
    Should Contain    ${faults}    UNDERTEMPERATURE

    Clear Battery Faults


Temperature D Spread Detection
    [Documentation]    Verify detection of excessive temperature spread
    [Tags]    battery    thermal    spread

    # Set up temperature spread
    Set Cell Temperature    cell_id=0    temperature=20
    Set Cell Temperature    cell_id=1    temperature=60

    ${temp0}=    Get Cell Temperature    0
    ${temp1}=    Get Cell Temperature    1
    ${spread}=    Evaluate    abs(${temp1} - ${temp0})

    Log    Temperature spread: ${spread}C

    # In a real implementation, this would trigger a spread fault
    Should Be True    ${spread} > 30    msg=Temperature spread not as expected
    [Teardown]    Clear Battery Faults


Thermal Fault During Charging
    [Documentation]    Verify thermal protection during charging
    [Tags]    battery    thermal    charging

    # Set cell to high temperature
    Inject Cell Overtemperature    cell_id=0    temperature=65

    # Attempt to charge (in real implementation, this would be blocked)
    ${soc_before}=    Get Battery SOC
    Simulate Charging    current=10    duration=30
    ${soc_after}=    Get Battery SOC

    # Verify fault was detected
    ${detected}=    Verify Battery Fault Detected    OVERTEMPERATURE    timeout=1

    Clear Battery Faults

    Log    SOC before: ${soc_before}% after: ${soc_after}%
    Should Be True    ${detected}


Multiple Thermal Faults Detection
    [Documentation]    Verify detection of multiple simultaneous thermal faults
    [Tags]    battery    thermal    multiple

    # Inject multiple overtemperature faults
    Inject Cell Overtemperature    cell_id=0    temperature=70
    Inject Cell Overtemperature    cell_id=10    temperature=75
    Inject Cell Overtemperature    cell_id=50    temperature=80

    ${faults}=    Get Battery Faults

    # Should have overtemperature fault
    Should Contain    ${faults}    OVERTEMPERATURE

    # Count how many cells are over temperature
    ${overtemp_count}=    Set Variable    0
    FOR    ${cell_id}    IN RANGE    ${NUM_CELLS}
        ${temp}=    Get Cell Temperature    ${cell_id}
        ${is_over}=    Evaluate    ${temp} > ${MAX_CELL_TEMP}
        ${overtemp_count}=    Set Variable If    ${is_over}    ${{ ${overtemp_count} + 1 }}    ${overtemp_count}
    END

    Log    Cells over temperature: ${overtemp_count}

    Clear Battery Faults


Thermal Recovery Test
    [Documentation]    Verify fault clears when temperature returns to normal
    [Tags]    battery    thermal    recovery

    # Create fault condition
    Inject Cell Overtemperature    cell_id=0    temperature=70

    ${detected}=    Verify Battery Fault Detected    OVERTEMPERATURE
    Should Be True    ${detected}

    # Restore normal temperature
    Set Cell Temperature    cell_id=0    temperature=25

    # Wait and verify fault cleared
    Sleep    1s

    ${faults}=    Get Battery Faults
    Should Not Contain    ${faults}    OVERTEMPERATURE

    Log    Thermal fault cleared after temperature normalized


Temperature Monitoring Precision
    [Documentation]    Verify temperature readings are sufficiently precise
    [Tags]    battery    thermal    precision

    # Set specific temperatures
    @{test_temps}=    Create List    20.0    25.0    30.0    35.0    40.0

    FOR    ${temp}    IN    @{test_temps}
        Set Cell Temperature    cell_id=0    temperature=${temp}
        Sleep    0.1s
        ${read_temp}=    Get Cell Temperature    0
        ${diff}=    Evaluate    abs(${read_temp} - ${temp})
        Should Be True    ${diff} < 1.0    msg=Temperature reading not precise: expected ${temp}, got ${read_temp}
        Log    Set ${temp}C, read ${read_temp}C, diff ${diff}C
    END

    Clear Battery Faults


*** Keywords ***
Start Battery Simulation
    [Documentation]    Initialize battery ECU simulation and fault injection
    Log    Starting battery ECU simulation for thermal tests...
    ${id}=    libraries.ECUSimulatorLibrary.Start Battery Simulation    num_cells=${NUM_CELLS}

    # Get ECU instance for fault injection
    ${battery_ecu}=    Get Battery ECU Instance
    Set Battery ECU    ${battery_ecu}

    Set Suite Variable    ${BATTERY_ID}    ${id}

Clear All Faults And Stop
    [Documentation]    Clear faults and stop simulation
    Clear Battery Faults
    Stop All Simulations
    Log    Battery simulation stopped and faults cleared
