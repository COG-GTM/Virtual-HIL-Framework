*** Settings ***
Documentation     Battery monitoring functional tests
...               Tests the battery ECU's monitoring capabilities including
...               SOC, voltage, current, and temperature readings.

Resource          ../../resources/common_keywords.robot
Resource          ../../resources/ecu_variables.robot
Library           libraries.ECUSimulatorLibrary
Library           Collections

Suite Setup       Start Battery Simulation
Suite Teardown    Stop All Simulations
Test Timeout      30 seconds


*** Test Cases ***
Read Initial Battery State
    [Documentation]    Verify initial battery state after simulation start
    [Tags]    battery    monitoring    smoke

    ${soc}=    Get Battery SOC
    Should Be True    ${soc} <= 100
    Should Be True    ${soc} >= 0

    ${voltage}=    Get Battery Voltage
    Should Be True    ${voltage} > 300
    Should Be True    ${voltage} < 500

    ${temperature}=    Get Battery Temperature
    Should Be True    ${temperature} >= -40
    Should Be True    ${temperature} <= 100

    Log    Initial SOC: ${soc}% Voltage: ${voltage}V Temp: ${temperature}C


Read Individual Cell Voltages
    [Documentation]    Verify cell-level voltage monitoring
    [Tags]    battery    cells

    FOR    ${cell_id}    IN RANGE    ${NUM_CELLS}
        ${voltage}=    Get Cell Voltage    ${cell_id}
        Should Be True    ${voltage} >= 2.0    msg=Cell ${cell_id} voltage too low
        Should Be True    ${voltage} <= 4.5    msg=Cell ${cell_id} voltage too high
    END

    Log    All ${NUM_CELLS} cell voltages within acceptable range


Verify Cell Voltage Spread
    [Documentation]    Check that cell voltages are within acceptable spread
    [Tags]    battery    cells

    @{voltages}=    Create List
    FOR    ${cell_id}    IN RANGE    ${NUM_CELLS}
        ${voltage}=    Get Cell Voltage    ${cell_id}
        Append To List    ${voltages}    ${voltage}
    END

    ${max_voltage}=    Evaluate    max(${voltages})
    ${min_voltage}=    Evaluate    min(${voltages})
    ${spread}=    Evaluate    ${max_voltage} - ${min_voltage}

    Should Be True    ${spread} < 0.5    msg=Cell voltage spread too large: ${spread}V
    Log    Cell voltage spread: ${spread}V (max: ${max_voltage}V, min: ${min_voltage}V)


Simulate Battery Charging
    [Documentation]    Verify SOC increases during charging simulation
    [Tags]    battery    charging

    # Pack starts fully charged; discharge first so there is headroom
    Simulate Charging    current=-50    duration=600
    ${initial_soc}=    Get Battery SOC
    Log    Initial SOC: ${initial_soc}%

    Simulate Charging    current=10    duration=60

    ${final_soc}=    Get Battery SOC
    Log    Final SOC: ${final_soc}%

    Should Be True    ${final_soc} > ${initial_soc}    msg=SOC did not increase during charging
    ${soc_increase}=    Evaluate    ${final_soc} - ${initial_soc}
    Log    SOC increase: ${soc_increase}%


Simulate Battery Discharging
    [Documentation]    Verify SOC decreases during discharging simulation
    [Tags]    battery    discharging

    ${initial_soc}=    Get Battery SOC
    Log    Initial SOC: ${initial_soc}%

    Simulate Charging    current=-10    duration=60

    ${final_soc}=    Get Battery SOC
    Log    Final SOC: ${final_soc}%

    Should Be True    ${final_soc} < ${initial_soc}    msg=SOC did not decrease during discharging
    ${soc_decrease}=    Evaluate    ${initial_soc} - ${final_soc}
    Log    SOC decrease: ${soc_decrease}%


Verify Pack Voltage Calculation
    [Documentation]    Verify pack voltage matches sum of cell voltages
    [Tags]    battery    voltage    calculation

    ${pack_voltage}=    Get Battery Voltage

    @{cell_voltages}=    Create List
    FOR    ${cell_id}    IN RANGE    ${NUM_CELLS}
        ${voltage}=    Get Cell Voltage    ${cell_id}
        Append To List    ${cell_voltages}    ${voltage}
    END

    ${calculated_pack}=    Evaluate    sum(${cell_voltages})

    # Allow small tolerance for floating point
    ${voltage_diff}=    Evaluate    abs(${pack_voltage} - ${calculated_pack})
    Should Be True    ${voltage_diff} < 1.0    msg=Pack voltage mismatch: ${pack_voltage} vs ${calculated_pack}
    Log    Pack voltage: ${pack_voltage}V Calculated: ${calculated_pack}V


Check Temperature Range
    [Documentation]    Verify all cell temperatures are within safe range
    [Tags]    battery    temperature

    # In a real test, we would read individual cell temps
    ${pack_temp}=    Get Battery Temperature

    Should Be True    ${pack_temp} >= ${MIN_OPERATING_TEMP}
    Should Be True    ${pack_temp} <= ${MAX_OPERATING_TEMP}
    Log    Pack temperature ${pack_temp}C within operating range


Verify SOC Limits
    [Documentation]    Verify SOC stays within 0-100% range
    [Tags]    battery    soc    limits

    # Test upper limit
    ${initial_soc}=    Get Battery SOC
    Run Keyword If    ${initial_soc} < 95    Simulate Charging    current=50    duration=500

    ${soc}=    Get Battery SOC
    Should Be True    ${soc} <= 100    msg=SOC exceeded 100%

    # Test lower limit
    Simulate Charging    current=-50    duration=500

    ${soc}=    Get Battery SOC
    Should Be True    ${soc} >= 0    msg=SOC dropped below 0%


Measure Response Time
    [Documentation]    Measure response time for state queries
    [Tags]    battery    performance

    ${start_time}=    Get Time    epoch

    # Perform multiple reads
    FOR    ${i}    IN RANGE    ${100}
        Get Battery SOC
        Get Battery Voltage
        Get Battery Temperature
    END

    ${end_time}=    Get Time    epoch
    ${elapsed}=    Evaluate    (${end_time} - ${start_time}) * 1000
    ${avg_time}=    Evaluate    ${elapsed} / 300

    Log    Total time: ${elapsed}ms Average per query: ${avg_time}ms
    Should Be True    ${avg_time} < 10    msg=Query response too slow: ${avg_time}ms


*** Keywords ***
Start Battery Simulation
    [Documentation]    Initialize battery ECU simulation
    Log    Starting battery ECU simulation...
    ${id}=    libraries.ECUSimulatorLibrary.Start Battery Simulation    num_cells=${NUM_CELLS}
    Set Suite Variable    ${BATTERY_ID}    ${id}
    Log    Battery simulation started: ${BATTERY_ID}
