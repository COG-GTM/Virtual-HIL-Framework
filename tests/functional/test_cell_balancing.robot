*** Settings ***
Documentation     Cell balancing functional tests
...               Tests the battery ECU's cell balancing capabilities.

Resource          ../../resources/common_keywords.robot
Resource          ../../resources/ecu_variables.robot
Library           libraries.ECUSimulatorLibrary
Library           Collections

Suite Setup       Start Battery Simulation
Suite Teardown    Stop All Simulations
Test Timeout      30 seconds


*** Test Cases ***
Verify Cell Balancing Function
    [Documentation]    Verify that cell balancing reduces voltage spread
    [Tags]    battery    balancing    critical

    # First, create voltage imbalance
    Set Cell Voltage    cell_id=0    voltage=4.0
    Set Cell Voltage    cell_id=1    voltage=3.4

    ${v1_before}=    Get Cell Voltage    0
    ${v2_before}=    Get Cell Voltage    1
    ${spread_before}=    Evaluate    abs(${v1_before} - ${v2_before})

    Log    Before balancing - Cell 0: ${v1_before}V Cell 1: ${v2_before}V Spread: ${spread_before}V

    # Run balancing
    Balance Cells

    # Wait a moment for balancing to take effect
    Sleep    1s

    ${v1_after}=    Get Cell Voltage    0
    ${v2_after}=    Get Cell Voltage    1
    ${spread_after}=    Evaluate    abs(${v1_after} - ${v2_after})

    Log    After balancing - Cell 0: ${v1_after}V Cell 1: ${v2_after}V Spread: ${spread_after}V

    # Verify spread decreased
    Should Be True    ${spread_after} < ${spread_before}    msg=Cell balancing did not reduce voltage spread


Balancing Reduces Max Spread
    [Documentation]    Verify balancing reduces the maximum cell spread
    [Tags]    battery    balancing

    # Create significant imbalance across multiple cells
    Set Cell Voltage    cell_id=0    voltage=4.1
    Set Cell Voltage    cell_id=10    voltage=3.3
    Set Cell Voltage    cell_id=50    voltage=4.0
    Set Cell Voltage    cell_id=80    voltage=3.4

    @{voltages_before}=    Create List
    FOR    ${cell_id}    IN RANGE    ${NUM_CELLS}
        ${voltage}=    Get Cell Voltage    ${cell_id}
        Append To List    ${voltages_before}    ${voltage}
    END

    ${max_before}=    Evaluate    max(${voltages_before})
    ${min_before}=    Evaluate    min(${voltages_before})
    ${spread_before}=    Evaluate    ${max_before} - ${min_before}

    Log    Max spread before balancing: ${spread_before}V

    # Run multiple balancing cycles (each cycle closes 10% of the gap)
    FOR    ${i}    IN RANGE    ${10}
        Balance Cells
        Sleep    0.2s
    END

    @{voltages_after}=    Create List
    FOR    ${cell_id}    IN RANGE    ${NUM_CELLS}
        ${voltage}=    Get Cell Voltage    ${cell_id}
        Append To List    ${voltages_after}    ${voltage}
    END

    ${max_after}=    Evaluate    max(${voltages_after})
    ${min_after}=    Evaluate    min(${voltages_after})
    ${spread_after}=    Evaluate    ${max_after} - ${min_after}

    Log    Max spread after balancing: ${spread_after}V

    Should Be True    ${spread_after} < ${spread_before} * 0.5    msg=Balancing did not sufficiently reduce spread


Balancing Does Not Affect Average Voltage
    [Documentation]    Verify balancing does not significantly change pack average
    [Tags]    battery    balancing

    # Get initial average
    @{voltages_before}=    Create List
    FOR    ${cell_id}    IN RANGE    ${NUM_CELLS}
        ${voltage}=    Get Cell Voltage    ${cell_id}
        Append To List    ${voltages_before}    ${voltage}
    END
    ${avg_before}=    Evaluate    sum(${voltages_before}) / len(${voltages_before})

    # Balance
    Balance Cells
    Sleep    1s

    # Get final average
    @{voltages_after}=    Create List
    FOR    ${cell_id}    IN RANGE    ${NUM_CELLS}
        ${voltage}=    Get Cell Voltage    ${cell_id}
        Append To List    ${voltages_after}    ${voltage}
    END
    ${avg_after}=    Evaluate    sum(${voltages_after}) / len(${voltages_after})

    # Average should be similar (within 5%)
    ${avg_diff}=    Evaluate    abs(${avg_after} - ${avg_before})
    ${percent_diff}=    Evaluate    (${avg_diff} / ${avg_before}) * 100

    Log    Average before: ${avg_before}V after: ${avg_after}V diff: ${percent_diff}%
    Should Be True    ${percent_diff} < 5    msg=Average voltage changed too much during balancing


Continuous Balancing During Charge
    [Documentation]    Verify balancing works during simulated charging
    [Tags]    battery    balancing    charging

    # Create imbalance
    Set Cell Voltage    cell_id=0    voltage=4.0
    Set Cell Voltage    cell_id=1    voltage=3.5

    ${v1_before}=    Get Cell Voltage    0
    ${v2_before}=    Get Cell Voltage    1

    # Simulate charging with balancing
    FOR    ${i}    IN RANGE    ${10}
        Simulate Charging    current=5    duration=10
        Balance Cells
        Sleep    0.1s
    END

    ${v1_after}=    Get Cell Voltage    0
    ${v2_after}=    Get Cell Voltage    1
    ${spread}=    Evaluate    abs(${v1_after} - ${v2_after})

    Log    After charge-balance cycle - Cell 0: ${v1_after}V Cell 1: ${v2_after}V Spread: ${spread}V

    # Spread should be small after multiple cycles
    Should Be True    ${spread} < 0.2    msg=Cell spread too large after charge-balancing


Balancing Performance Test
    [Documentation]    Measure time required for balancing operation
    [Tags]    battery    balancing    performance

    ${start_time}=    Get Time    epoch

    FOR    ${i}    IN RANGE    ${50}
        Balance Cells
    END

    ${end_time}=    Get Time    epoch
    ${elapsed}=    Evaluate    (${end_time} - ${start_time}) * 1000
    ${avg_time}=    Evaluate    ${elapsed} / 50

    Log    Total time for 50 balance cycles: ${elapsed}ms
    Log    Average time per cycle: ${avg_time}ms

    Should Be True    ${avg_time} < 100    msg=Balancing operation too slow: ${avg_time}ms


*** Keywords ***
Start Battery Simulation
    [Documentation]    Initialize battery ECU simulation
    Log    Starting battery ECU simulation for cell balancing tests...
    ${id}=    libraries.ECUSimulatorLibrary.Start Battery Simulation    num_cells=${NUM_CELLS}
    Set Suite Variable    ${BATTERY_ID}    ${id}
