"""
INA228 Power Monitor interface for voltage and current measurement.
"""

from typing import Tuple, Optional

# Hardware imports - will fail gracefully on non-Pi systems
try:
    import board
    import busio
    import adafruit_ina228
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False


class PowerMonitor:
    """
    Interface for INA228 power monitor.

    Provides voltage, current, and power measurements for
    thruster characterization.
    """

    def __init__(self, address: int = 0x41, simulate: bool = False):
        """
        Initialize power monitor.

        Args:
            address: I2C address of INA228 (default 0x41)
            simulate: If True, simulate hardware for testing
        """
        self.address = address
        self.simulate = simulate or not HARDWARE_AVAILABLE

        self._ina: Optional[adafruit_ina228.INA228] = None

        # Simulated values for testing
        self._sim_voltage = 12.0
        self._sim_current = 0.0

        if not self.simulate:
            self._init_hardware()

    def _init_hardware(self):
        """Initialize INA228 hardware."""
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self._ina = adafruit_ina228.INA228(i2c, address=self.address)
        except Exception as e:
            print(f"Failed to initialize INA228: {e}")
            self.simulate = True

    def read_voltage(self) -> float:
        """
        Read bus voltage in Volts.

        Returns:
            Voltage in Volts
        """
        if self.simulate:
            return self._sim_voltage

        try:
            return self._ina.bus_voltage
        except Exception as e:
            print(f"Failed to read voltage: {e}")
            return 0.0

    def read_current(self) -> float:
        """
        Read current in Amps.

        Returns:
            Current in Amps
        """
        if self.simulate:
            return self._sim_current

        try:
            return self._ina.current
        except Exception as e:
            print(f"Failed to read current: {e}")
            return 0.0

    def read_power(self) -> float:
        """
        Read power in Watts.

        Returns:
            Power in Watts
        """
        if self.simulate:
            return self._sim_voltage * self._sim_current

        try:
            return self._ina.power
        except Exception as e:
            print(f"Failed to read power: {e}")
            return 0.0

    def read_all(self) -> Tuple[float, float, float]:
        """
        Read all measurements at once.

        Returns:
            Tuple of (voltage_v, current_a, power_w)
        """
        voltage = self.read_voltage()
        current = self.read_current()
        power = self.read_power()
        return voltage, current, power

    def set_simulated_values(self, voltage: float, current: float):
        """
        Set simulated values for testing.

        Args:
            voltage: Simulated voltage in Volts
            current: Simulated current in Amps
        """
        self._sim_voltage = voltage
        self._sim_current = current

    def is_connected(self) -> bool:
        """Check if sensor is connected and responding."""
        if self.simulate:
            return True

        try:
            # Try to read a value to verify connection
            _ = self._ina.bus_voltage
            return True
        except Exception:
            return False

    def cleanup(self):
        """Clean up resources."""
        # INA228 doesn't need explicit cleanup
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False
