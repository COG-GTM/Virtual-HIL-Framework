#!/usr/bin/env python3
"""
Virtual HIL Framework - ECU Simulator Startup Script

This script starts and manages ECU simulators for the Virtual HIL Framework.
Works cross-platform on Windows, Linux, and macOS.
"""

import argparse
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


class Colors:
    """ANSI color codes for terminal output (Windows compatible)"""

    @staticmethod
    def init():
        """Initialize colors for Windows"""
        if platform.system() == "Windows":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


class ECUSimulatorManager:
    """Manages ECU simulator processes"""

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            self.project_root = Path(__file__).parent.parent
        else:
            self.project_root = project_root

        self.log_dir = self.project_root / "logs"
        self.pid_dir = self.project_root / ".pids"

        # Create directories
        self.log_dir.mkdir(exist_ok=True)
        self.pid_dir.mkdir(exist_ok=True)

    def _log_info(self, message: str):
        print(f"{Colors.GREEN}[INFO]{Colors.NC} {message}")

    def _log_warn(self, message: str):
        print(f"{Colors.YELLOW}[WARN]{Colors.NC} {message}")

    def _log_error(self, message: str):
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

    def _get_pid_file(self, name: str) -> Path:
        return self.pid_dir / f"{name}.pid"

    def _get_log_file(self, name: str) -> Path:
        return self.log_dir / f"{name}.log"

    def _is_running(self, name: str) -> bool:
        """Check if a process is running"""
        pid_file = self._get_pid_file(name)
        if not pid_file.exists():
            return False

        try:
            pid = int(pid_file.read_text().strip())
            if platform.system() == "Windows":
                # Windows: use tasklist to check if process exists
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True,
                    text=True,
                )
                # Check if PID is in output (more reliable check)
                return str(pid) in result.stdout and "Not Found" not in result.stdout
            else:
                # Unix: use kill -0 to check if process exists
                os.kill(pid, 0)
                return True
        except (ProcessLookupError, ValueError, OSError):
            return False

    def _start_process(
        self, name: str, command: list[str], description: str
    ) -> bool:
        """Start a process in the background"""
        if self._is_running(name):
            self._log_warn(f"{description} is already running")
            return True

        self._log_info(f"Starting {description}...")
        self._log_info(f"  Command: {' '.join(command)}")

        log_file = self._get_log_file(name)
        pid_file = self._get_pid_file(name)

        try:
            # Open log file
            log_fp = open(log_file, "w")

            if platform.system() == "Windows":
                # Windows: use DETACHED_PROCESS to completely detach from parent
                # This allows the process to continue running after parent exits
                DETACHED_PROCESS = 0x00000008
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=log_fp,
                    stderr=subprocess.STDOUT,
                    creationflags=DETACHED_PROCESS,
                    close_fds=False,  # Don't close fds to allow file handles to work
                )
            else:
                # Unix: use nohup-like behavior
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=log_fp,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )

            pid_file.write_text(str(process.pid))
            self._log_info(f"{description} started (PID: {process.pid})")
            self._log_info(f"  Log: {log_file}")

            # Wait longer to allow the process to fully initialize
            time.sleep(1.5)
            if process.poll() is not None:
                # Process exited immediately
                self._log_error(f"{description} exited immediately")
                self._log_error(f"  Check log: {log_file}")
                # Show last few lines of log
                try:
                    with open(log_file, "r") as f:
                        lines = f.readlines()
                        if lines:
                            self._log_error("  Last log lines:")
                            for line in lines[-5:]:
                                self._log_error(f"    {line.rstrip()}")
                except Exception:
                    pass
                return False

            return True

        except Exception as e:
            self._log_error(f"Failed to start {description}: {e}")
            return False

    def _stop_process(self, name: str, description: str) -> bool:
        """Stop a running process"""
        if not self._is_running(name):
            self._log_warn(f"{description} is not running")
            return True

        pid_file = self._get_pid_file(name)

        try:
            pid = int(pid_file.read_text().strip())

            if platform.system() == "Windows":
                # Windows: use taskkill
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                )
            else:
                # Unix: use SIGTERM
                os.kill(pid, signal.SIGTERM)

            self._log_info(f"{description} stopped (PID: {pid})")
            pid_file.unlink(missing_ok=True)
            return True

        except Exception as e:
            self._log_error(f"Failed to stop {description}: {e}")
            return False

    def start_battery_ecu(self) -> bool:
        """Start the Battery ECU simulator"""
        # Use pythonw.exe on Windows for background processes (no console)
        python_exe = self._get_python_executable()
        command = [
            python_exe,
            "-m",
            "ecu_simulation.battery_ecu",
        ]
        return self._start_process("battery_ecu", command, "Battery ECU")

    def start_battery_ecu_server(self) -> bool:
        """Start the Battery ECU FastAPI server"""
        # Use pythonw.exe on Windows for background processes (no console)
        python_exe = self._get_python_executable()
        command = [
            python_exe,
            "-m",
            "ecu_simulation.battery_ecu_server",
        ]
        return self._start_process("battery_ecu_server", command, "Battery ECU Server")

    def start_door_ecu(self) -> bool:
        """Start the Door ECU simulator"""
        # Use pythonw.exe on Windows for background processes (no console)
        python_exe = self._get_python_executable()
        command = [
            python_exe,
            "-m",
            "ecu_simulation.door_ecu",
        ]
        return self._start_process("door_ecu", command, "Door ECU")

    def _get_python_executable(self) -> str:
        """Get the appropriate Python executable for background processes"""
        if platform.system() == "Windows":
            # Use pythonw.exe for background processes (no console window)
            venv_dir = Path(sys.executable).parent
            pythonw = venv_dir / "pythonw.exe"
            if pythonw.exists():
                return str(pythonw)
        return sys.executable

    def start_all(self, with_server: bool = True) -> bool:
        """Start all ECU simulators"""
        self._log_info("Starting ECU simulators...")
        success = True

        if with_server:
            success &= self.start_battery_ecu_server()
        else:
            success &= self.start_battery_ecu()

        success &= self.start_door_ecu()

        if success:
            self._log_info(f"{Colors.GREEN}All simulators started{Colors.NC}")
            time.sleep(1)
            self.show_status()
        else:
            self._log_error("Some simulators failed to start")

        return success

    def stop_all(self) -> bool:
        """Stop all running simulators"""
        self._log_info("Stopping all simulators...")
        success = True

        simulators = ["battery_ecu_server", "battery_ecu", "door_ecu"]

        for sim in simulators:
            description = sim.replace("_", " ").title()
            success &= self._stop_process(sim, description)

        if success:
            self._log_info(f"{Colors.GREEN}All simulators stopped{Colors.NC}")

        return success

    def restart_all(self, with_server: bool = True) -> bool:
        """Restart all simulators"""
        self.stop_all()
        time.sleep(2)
        return self.start_all(with_server=with_server)

    def show_status(self):
        """Show status of all simulators"""
        self._log_info("ECU Simulator Status:")

        simulators = [
            ("battery_ecu_server", "Battery ECU Server"),
            ("battery_ecu", "Battery ECU"),
            ("door_ecu", "Door ECU"),
        ]

        has_any = False

        for sim, name in simulators:
            pid_file = self._get_pid_file(sim)

            if pid_file.exists():
                has_any = True
                pid = pid_file.read_text().strip()

                if self._is_running(sim):
                    status = f"{Colors.GREEN}[+]{Colors.NC} Running"
                    print(f"  {status} {name} (PID: {pid})")
                else:
                    status = f"{Colors.RED}[-]{Colors.NC} Stopped"
                    print(f"  {status} {name} (stale PID file)")

        if not has_any:
            print(f"  {Colors.YELLOW}No simulators configured{Colors.NC}")

    def follow_log(self, name: str):
        """Follow the log file of a simulator"""
        log_file = self._get_log_file(name)

        if not log_file.exists():
            self._log_error(f"Log file not found: {log_file}")
            return

        self._log_info(f"Following {name} log (Ctrl+C to exit)...")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}")

        try:
            with open(log_file, "r") as f:
                # Seek to end
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        print(line.rstrip())
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
            self._log_info("Stopped following log")


def main():
    """Main entry point for the console script"""
    # Fix Windows console encoding
    if platform.system() == "Windows":
        import io

        # Set UTF-8 mode for Windows console
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    Colors.init()

    parser = argparse.ArgumentParser(
        description="Virtual HIL Framework - ECU Simulator Control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vhil-start start              # Start all simulators (with HTTP server)
  vhil-start start --no-server  # Start simulators without HTTP server
  vhil-start stop               # Stop all simulators
  vhil-start restart            # Restart all simulators
  vhil-start status             # Show simulator status
  vhil-start logs battery_ecu_server  # Follow server logs
        """,
    )

    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "status", "logs"],
        nargs="?",
        default="start",
        help="Command to execute",
    )

    parser.add_argument(
        "--no-server",
        action="store_true",
        help="Start ECU simulators without the HTTP server",
    )

    parser.add_argument(
        "--simulator",
        "-s",
        help="Simulator name for 'logs' command",
    )

    args = parser.parse_args()

    manager = ECUSimulatorManager()

    match args.command:
        case "start":
            success = manager.start_all(with_server=not args.no_server)
            sys.exit(0 if success else 1)

        case "stop":
            success = manager.stop_all()
            sys.exit(0 if success else 1)

        case "restart":
            success = manager.restart_all(with_server=not args.no_server)
            sys.exit(0 if success else 1)

        case "status":
            manager.show_status()

        case "logs":
            simulator = args.simulator or "battery_ecu_server"
            manager.follow_log(simulator)


if __name__ == "__main__":
    main()
