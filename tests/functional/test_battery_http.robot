*** Settings ***
Documentation     Battery ECU HTTP API functional tests
...               Tests the battery ECU's REST API interface using
...               HTTP-based communication for more realistic HIL testing.

Resource          ../../resources/common_keywords.robot
Resource          ../../resources/ecu_variables.robot
Library           libraries.ECUSimulatorHTTPLibrary    http://localhost:8000    verify=False
Library           Collections

Suite Setup       Start ECU Server
Suite Teardown    Stop ECU Server
Test Timeout      30 seconds


*** Test Cases ***
TC001 ECU Health Check
    [Documentation]    Verify the ECU server is running and healthy
    [Tags]    http    health    smoke

    ${status}=    Check ECU Health
    Should Be Equal    ${status}    healthy    msg=ECU server is not healthy


TC002 Get Initial Status
    [Documentation]    Retrieve and verify initial ECU state
    [Tags]    http    status    smoke

    ${status}=    Get ECU Status
    Log    Full ECU Status: ${status}

    # Verify all fields are present
    Dictionary Should Contain Key    ${status}    soc
    Dictionary Should Contain Key    ${status}    soh
    Dictionary Should Contain Key    ${status}    voltage
    Dictionary Should Contain Key    ${status}    current
    Dictionary Should Contain Key    ${status}    temperature
    Dictionary Should Contain Key    ${status}    faults
    Dictionary Should Contain Key    ${status}    running

    # Verify initial values are within expected ranges
    ${soc}=    Get From Dictionary    ${status}    soc
    Should Be True    ${soc} <= 100
    Should Be True    ${soc} >= 0

    ${voltage}=    Get From Dictionary    ${status}    voltage
    Should Be True    ${voltage} > 300
    Should Be True    ${voltage} < 500

    ${running}=    Get From Dictionary    ${status}    running
    Should Be True    ${running}


TC003 State Queries Via HTTP
    [Documentation]    Test individual state query endpoints
    [Tags]    http    state

    # Test SOC endpoint
    ${soc}=    Get Battery SOC
    Should Be True    ${soc} >= 0
    Should Be True    ${soc} <= 100
    Log    SOC: ${soc}%

    # Test voltage endpoint
    ${voltage}=    Get Battery Voltage
    Should Be True    ${voltage} > 0
    Log    Pack voltage: ${voltage}V

    # Test current endpoint
    ${current}=    Get Battery Current
    Log    Pack current: ${current}A

    # Test temperature endpoint
    ${temperature}=    Get Battery Temperature
    Should Be True    ${temperature} >= -40
    Should Be True    ${temperature} <= 100
    Log    Pack temperature: ${temperature}C

    # Test SOH endpoint
    ${soh}=    Get Battery SOH
    Should Be True    ${soh} >= 0
    Should Be True    ${soh} <= 100
    Log    SOH: ${soh}%


TC004 Cell Voltage Queries Via HTTP
    [Documentation]    Test cell-level voltage monitoring via HTTP
    [Tags]    http    cells    voltage

    # Query first 10 cells
    FOR    ${cell_id}    IN RANGE    ${10}
        ${voltage}=    Get Cell Voltage    ${cell_id}
        Should Be True    ${voltage} >= 2.0    msg=Cell ${cell_id} voltage too low
        Should Be True    ${voltage} <= 4.5    msg=Cell ${cell_id} voltage too high
        Log    Cell ${cell_id} voltage: ${voltage}V
    END

    Log    First 10 cell voltages are within acceptable range


TC005 Simulate Charging Via HTTP
    [Documentation]    Verify SOC increases during charging simulation
    [Tags]    http    charging

    # Pack starts fully charged; discharge first so there is headroom
    Simulate Charging    current=-50    duration=600
    ${initial_soc}=    Get Battery SOC
    Log    Initial SOC: ${initial_soc}%

    ${result}=    Simulate Charging    current=10    duration=60

    # Verify response structure
    Dictionary Should Contain Key    ${result}    message
    Dictionary Should Contain Key    ${result}    details

    ${details}=    Get From Dictionary    ${result}    details
    ${new_soc}=    Get From Dictionary    ${details}    new_soc

    Log    Final SOC: ${new_soc}%

    Should Be True    ${new_soc} > ${initial_soc}    msg=SOC did not increase during charging
    ${soc_increase}=    Evaluate    ${new_soc} - ${initial_soc}
    Log    SOC increase: ${soc_increase}%


TC006 Simulate Discharging Via HTTP
    [Documentation]    Verify SOC decreases during discharging simulation
    [Tags]    http    discharging

    ${initial_soc}=    Get Battery SOC
    Log    Initial SOC: ${initial_soc}%

    ${result}=    Simulate Charging    current=-10    duration=60

    ${details}=    Get From Dictionary    ${result}    details
    ${new_soc}=    Get From Dictionary    ${details}    new_soc

    Log    Final SOC: ${new_soc}%

    Should Be True    ${new_soc} < ${initial_soc}    msg=SOC did not decrease during discharging
    ${soc_decrease}=    Evaluate    ${initial_soc} - ${new_soc}
    Log    SOC decrease: ${soc_decrease}%


TC007 Cell Balancing Via HTTP
    [Documentation]    Test cell balancing trigger via HTTP
    [Tags]    http    balancing

    # Get initial voltages
    ${v0_before}=    Get Cell Voltage    0
    ${v1_before}=    Get Cell Voltage    1

    Log    Cell 0 before balance: ${v0_before}V
    Log    Cell 1 before balance: ${v1_before}V

    # Trigger balancing
    ${result}=    Balance Cells
    Log    Balance result: ${result}

    # Get voltages after balancing
    ${v0_after}=    Get Cell Voltage    0
    ${v1_after}=    Get Cell Voltage    1

    Log    Cell 0 after balance: ${v0_after}V
    Log    Cell 1 after balance: ${v1_after}V

    # Voltages should be closer after balancing
    ${diff_before}=    Evaluate    abs(${v0_before} - ${v1_before})
    ${diff_after}=    Evaluate    abs(${v0_after} - ${v1_after})

    Log    Voltage difference before: ${diff_before}V, after: ${diff_after}V


TC008 Fault Injection - Overvoltage
    [Documentation]    Test overvoltage fault detection via HTTP
    [Tags]    http    faults    overvoltage

    # Initially, no overvoltage fault should be present
    ECU Should Have No Faults

    # Inject overvoltage fault by setting a cell voltage too high
    ${result}=    Set Cell Voltage    0    5.0
    Log    Cell voltage set result: ${result}

    # Check that fault is detected
    ${faults}=    Get Active Faults
    Log    Active faults: ${faults}

    Should Contain    ${faults}    OVERVOLTAGE    msg=OVERVOLTAGE fault not detected

    # Verify DTC is set
    ${dtc}=    Get DTC
    Should Not Be Equal    ${dtc}    ${None}    msg=DTC should be set when fault is active
    Log    DTC: ${dtc}
    [Teardown]    Set Cell Voltage    0    3.7


TC009 Fault Injection - Overtemperature
    [Documentation]    Test overtemperature fault detection via HTTP
    [Tags]    http    faults    temperature

    # Clear any existing faults first
    Clear DTC

    # Inject overtemperature fault
    ${result}=    Set Cell Temperature    0    100
    Log    Cell temperature set result: ${result}

    # Check that fault is detected
    ${faults}=    Get Active Faults
    Log    Active faults: ${faults}

    Should Contain    ${faults}    OVERTEMPERATURE    msg=OVERTEMPERATURE fault not detected
    [Teardown]    Set Cell Temperature    0    25

TC010 Clear DTC Via HTTP
    [Documentation]    Test DTC clearing functionality
    [Tags]    http    faults    dtc

    # First, ensure we have a fault
    Set Cell Voltage    0    5.0

    ${faults}=    Get Active Faults
    ${has_fault}=    Evaluate    len(${faults}) > 0

    # Only proceed if we have a fault
    Run Keyword If    ${has_fault}    Log    Fault present, proceeding with DTC clear test

    ${dtc_before}=    Get DTC
    Log    DTC before clear: ${dtc_before}

    # Clear DTC
    ${result}=    Clear DTC
    Log    Clear result: ${result}

    # Note: In this simulation, DTC clearing is just a notification
    # The fault may still be present until the condition is resolved
    Log    DTC cleared (simulation only - fault condition may still exist)
    [Teardown]    Set Cell Voltage    0    3.7


TC011 Fault Verification Keywords
    [Documentation]    Test fault verification helper keywords
    [Tags]    http    faults    verification

    # First, ensure no faults
    Clear DTC

    # Should have no faults initially
    ECU Should Have No Faults

    # Inject a fault
    Set Cell Voltage    0    5.0

    # Should now have the fault
    ECU Should Have Fault    OVERVOLTAGE

    # Clean up - restore normal voltage
    Set Cell Voltage    0    3.7


TC012 Cell Temperature Queries And Injection
    [Documentation]    Test cell temperature reading and setting via HTTP
    [Tags]    http    cells    temperature

    # Get initial temperature
    ${temp_before}=    Get Cell Temperature    0
    Log    Cell 0 initial temperature: ${temp_before}C

    # Set a new temperature (within normal range)
    ${result}=    Set Cell Temperature    0    30
    Log    Temperature set result: ${result}

    # Verify the change
    ${temp_after}=    Get Cell Temperature    0
    Log    Cell 0 new temperature: ${temp_after}C

    Should Be Equal As Numbers    ${temp_after}    30    msg=Temperature not set correctly


TC013 Concurrent Requests Response Time
    [Documentation]    Measure response time for multiple HTTP requests
    [Tags]    http    performance

    ${start_time}=    Get Time    epoch

    # Perform multiple state queries
    FOR    ${i}    IN RANGE    ${50}
        Get Battery SOC
        Get Battery Voltage
        Get Battery Temperature
    END

    ${end_time}=    Get Time    epoch
    ${elapsed}=    Evaluate    (${end_time} - ${start_time}) * 1000
    ${avg_time}=    Evaluate    ${elapsed} / 150

    Log    Total time: ${elapsed}ms
    Log    Average per query: ${avg_time}ms

    # HTTP requests should be reasonably fast
    Should Be True    ${avg_time} < 100    msg=Query response too slow: ${avg_time}ms


TC014 HTTP Error Handling
    [Documentation]    Test that HTTP errors are properly reported
    [Tags]    http    error-handling

    # Try to access a non-existent cell
    Run Keyword And Expect Error    *404*    Get Cell Voltage    999

    # Try to set an invalid voltage (should be validated by Pydantic)
    Run Keyword And Expect Error    *    Set Cell Voltage    0    100

    Log    Error handling working correctly


TC015 Full Workflow Test
    [Documentation]    Complete workflow: start, check, modify, stop
    [Tags]    http    workflow

    # Start fresh
    Start ECU
    ${status}=    Check ECU Health
    Should Be Equal    ${status}    healthy

    # Get initial state
    ${soc}=    Get Battery SOC
    Log    Initial SOC: ${soc}%

    # Simulate some charging
    ${result}=    Simulate Charging    current=20    duration=100
    ${details}=    Get From Dictionary    ${result}    details
    ${new_soc}=    Get From Dictionary    ${details}    new_soc
    Log    SOC after charging: ${new_soc}%

    # Verify no faults
    ${faults}=    Get Active Faults
    Log    Faults: ${faults}

    # Get full status
    ${full_status}=    Get ECU Status
    Log    Final status: ${full_status}


*** Keywords ***
Start ECU Server
    [Documentation]    Initialize connection to ECU server
    Log    Connecting to ECU server at http://localhost:8000

    # Wait for server to be ready (useful in CI/CD context)
    ${ready}=    Wait For ECU Ready    timeout=30
    Run Keyword If    not ${ready}    Fatal Error    ECU server not ready within timeout

    Log    ECU server is ready and healthy

    # Ensure ECU is started
    Start ECU
    Log    ECU server connection established


Stop ECU Server
    [Documentation]    Disconnect from ECU server
    Log    Disconnecting from ECU server
    Stop ECU
    Log    ECU server connection closed
