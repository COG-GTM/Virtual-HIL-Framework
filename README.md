# Virtual HIL Framework

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Robot Framework](https://img.shields.io/badge/Robot_Framework-6.0+-darkgreen?logo=robotframework&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-teal?logo=fastapi&logoColor=white)
![UV](https://img.shields.io/badge/UV-Package_Manager-yellow?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue?logo=githubactions&logoColor=white)

A portfolio project demonstrating modern automotive test automation using Robot Framework with UV package management and REST API-based Virtual ECU simulation to replicate Hardware-in-the-Loop (HIL) testing workflows.

![Virtual HIL Framework Architecture](docs/images/repo_desc.png)

## Features

- **ECU Simulation**: Battery Management System (BMS), Body Domain Controller (BDC/Door)
- **CAN Communication**: Virtual CAN bus with message logging and monitoring
- **UDS Diagnostics**: Full ISO 14229 diagnostic server implementation
- **Fault Injection**: Comprehensive fault injection for testing
- **Robot Framework Integration**: Ready-to-use test libraries
- **Docker Support**: Containerized deployment
- **CI/CD Ready**: GitHub Actions workflows

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Virtual-HIL-Framework.git
cd Virtual-HIL-Framework

# Install dependencies
uv sync
```

### Running Tests

```bash
# Run all tests
uv run robot --pythonpath ./libraries:./ecu_simulation --outputdir reports tests/

# Run specific test suite
uv run robot --pythonpath ./libraries:./ecu_simulation --outputdir reports tests/functional/test_battery_monitoring.robot

# Run with tags
uv run robot --pythonpath ./libraries:./ecu_simulation --outputdir reports --include smoke tests/
```

### Running with Docker

```bash
# Start all ECUs
docker-compose up -d

# Run tests
docker-compose --profile test run --rm test-runner

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Project Structure

```
Virtual-HIL-Framework/
├── ecu_simulation/          # ECU simulation modules
│   ├── battery_ecu.py       # Battery Management System
│   ├── door_ecu.py          # Body Domain Controller
│   ├── can_interface.py     # CAN bus interface
│   ├── diagnostic_server.py # UDS diagnostic server
│   └── rest_interface.py    # REST API (optional)
├── libraries/               # Robot Framework libraries
│   ├── ECUSimulatorLibrary.py
│   ├── CANLibrary.py
│   ├── DiagnosticLibrary.py
│   └── FaultInjectionLibrary.py
├── tests/                   # Test suites
│   ├── functional/          # Functional tests
│   ├── diagnostic/          # Diagnostic tests
│   ├── integration/         # Integration tests
│   └── fault_injection/     # Fault injection tests
├── resources/               # Test resources
│   ├── common_keywords.robot
│   ├── ecu_variables.robot
│   └── test_data.robot
├── config/                  # Configuration files
│   ├── ecu_config.yaml
│   ├── can_database.dbc
│   └── diagnostic_database.json
├── scripts/                 # Utility scripts
│   ├── start_ecu_simulator.sh
│   ├── generate_can_trace.py
│   ├── analyze_logs.py
│   └── extract_stats.py
├── docker/                  # Docker configuration
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/                    # Documentation
│   ├── architecture.md
│   ├── ecu_specification.md
│   ├── test_strategy.md
│   └── ci_setup.md
├── pyproject.toml           # Project configuration
├── uv.lock                  # Dependency lock file
└── README.md
```

## Documentation

- [Architecture](docs/architecture.md) - System architecture and design
- [ECU Specifications](docs/ecu_specification.md) - ECU technical details
- [Test Strategy](docs/test_strategy.md) - Testing approach and guidelines
- [CI Setup](docs/ci_setup.md) - CI/CD configuration guide

## ECU Modules

### Battery ECU (BMS)

The Battery Management System simulator provides:
- 96-cell battery pack simulation
- Cell-level voltage and temperature monitoring
- State of Charge (SOC) estimation
- Cell balancing control
- Thermal management
- Fault detection (overvoltage, undervoltage, overtemperature, etc.)

### Door ECU (BDC)

The Body Domain Controller simulator provides:
- 4-door simulation with position control
- Lock/unlock functionality
- Window control
- Pinch protection (anti-trap)
- Child lock support
- Fault detection and reporting

## Robot Framework Libraries

### ECUSimulatorLibrary

Control and monitor ECU simulations:

```robot
*** Settings ***
Library           ECUSimulatorLibrary

*** Test Cases ***
Check Battery SOC
    Start Battery Simulation    num_cells=96
    ${soc}=    Get Battery SOC
    Should Be True    ${soc} > 80
    Stop All Simulations
```

### CANLibrary

Send and receive CAN messages:

```robot
*** Settings ***
Library           CANLibrary

*** Test Cases ***
Send CAN Message
    Start CAN Interface
    Send CAN Message    can_id=0x100    data=01A20405060708
    ${received}=    Wait For CAN Message    can_id=0x100    timeout=5
    Should Be True    ${received}
```

### DiagnosticLibrary

Perform UDS diagnostics:

```robot
*** Settings ***
Library           DiagnosticLibrary

*** Test Cases ***
Read ECU Info
    Start Diagnostic Session
    ${version}=    Read Software Version
    Log    ECU Software Version: ${version}
```

### FaultInjectionLibrary

Inject faults for testing:

```robot
*** Settings ***
Library           ECUSimulatorLibrary
Library           FaultInjectionLibrary

*** Test Cases ***
Test Overvoltage Detection
    Start Battery Simulation
    ${battery}=    Get Battery ECU Instance
    Set Battery ECU    ${battery}

    Inject Cell Overvoltage    cell_id=0    voltage=4.3
    ${detected}=    Verify Battery Fault Detected    OVERVOLTAGE
    Should Be True    ${detected}

    Clear All Faults

    Inject CAN Bus Timeout
    ${detected}=    Verify Battery Fault Detected    CAN_TIMEOUT
    Should Be True    ${detected}
```

## CAN Message Definitions

Standard CAN message IDs:

| ID     | Message               | Period  | Description                     |
|--------|-----------------------|---------|---------------------------------|
| 0x100  | BMS_Status            | 100ms   | Battery pack status             |
| 0x101  | BMS_Cell_Data         | 500ms   | Individual cell voltages        |
| 0x102  | BMS_Fault             | Event   | Battery fault indication        |
| 0x200  | BDC_Door_Status       | 100ms   | Door open/closed and lock status|
| 0x201  | BDC_Door_Position     | 50ms    | Door position percentage        |
| 0x202  | BDC_Window_Position   | 100ms   | Window position percentage      |

## UDS Diagnostic Services

Supported diagnostic services (ISO 14229):

| SID | Service                      | Description                     |
|-----|------------------------------|---------------------------------|
| 0x10| Diagnostic Session Control  | Change diagnostic session       |
| 0x22| Read Data By Identifier      | Read data identifiers           |
| 0x2E| Write Data By Identifier     | Write data identifiers          |
| 0x14| Clear DTC                    | Clear diagnostic trouble codes  |
| 0x19| Read DTC                     | Read stored DTCs                |
| 0x27| Security Access              | Security authentication         |
| 0x31| Routine Control              | Execute diagnostic routines     |
| 0x3E| Tester Present               | Keep session alive              |
| 0x85| Control DTC Setting          | Enable/disable DTC storage      |

## Development

### Adding a New ECU

1. Create new file in `ecu_simulation/`
2. Implement required methods:
   - `__init__(config_path)`
   - `to_dict()` - Export state
   - `check_faults()` - Return fault list
3. Update `ecu_simulation/__init__.py`
4. Add Robot Framework keywords to `ECUSimulatorLibrary.py`

### Adding Test Cases

1. Create `.robot` file in appropriate test directory
2. Use resources from `resources/` directory
3. Tag tests appropriately (smoke, critical, battery, door, etc.)
4. Follow naming conventions

## Configuration

ECU behavior is configured via `config/ecu_config.yaml`:

```yaml
battery_ecu:
  enabled: true
  can_id: 0x100
  pack:
    num_cells: 96
    cell_capacity_ah: 3.2
  voltage:
    max_cell_v: 4.2
    min_cell_v: 2.8
  # ... more configuration
```

## CI/CD

The framework includes GitHub Actions workflows:

- **SIL CI**: Runs on push/PR to main branches
- **Nightly Regression**: Daily full regression test
- **Manual HIL Test**: On-demand test execution

See [CI Setup](docs/ci_setup.md) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Robot Framework for excellent test automation framework
- ISO 14229 standard for UDS diagnostic specification
- Python CAN library for CAN bus communication

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/Virtual-HIL-Framework/issues
- Documentation: https://virtual-hil-framework.readthedocs.io/

## Roadmap

- [ ] Add more ECU types (Engine, Transmission, ABS, etc.)
- [ ] Implement additional UDS services
- [ ] Add real CAN hardware support
- [ ] Develop GUI for manual testing
- [ ] Create test case recorder
- [ ] Add performance benchmarking
- [ ] Implement test data management
