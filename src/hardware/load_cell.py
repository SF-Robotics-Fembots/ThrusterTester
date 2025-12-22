"""
HX711 Load Cell interface for thrust measurement.

This is a custom implementation for timing-sensitive GPIO operations
on Raspberry Pi.
"""

import time
from typing import Optional

# Hardware imports - will fail gracefully on non-Pi systems
try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False


class LoadCell:
    """
    Interface for HX711 load cell amplifier.

    The HX711 is a 24-bit ADC designed for weight scale applications.
    It uses a simple serial interface with DOUT (data) and SCK (clock) pins.
    """

    # Gain settings (number of clock pulses)
    GAIN_128 = 25  # Channel A, gain 128
    GAIN_64 = 27   # Channel A, gain 64
    GAIN_32 = 26   # Channel B, gain 32

    def __init__(self, dout_pin: int = 5, sck_pin: int = 6,
                 gain: int = GAIN_128, simulate: bool = False):
        """
        Initialize load cell interface.

        Args:
            dout_pin: GPIO pin for data output (BCM numbering)
            sck_pin: GPIO pin for serial clock (BCM numbering)
            gain: Gain setting (GAIN_128, GAIN_64, or GAIN_32)
            simulate: If True, simulate hardware for testing
        """
        self.dout_pin = dout_pin
        self.sck_pin = sck_pin
        self.gain = gain
        self.simulate = simulate or not HARDWARE_AVAILABLE

        # Calibration values
        self._offset = 0  # Tare offset (raw value at zero load)
        self._scale = 1.0  # Conversion factor (raw units per kg)

        # Simulated value
        self._sim_thrust = 0.0

        if not self.simulate:
            self._init_hardware()

    def _init_hardware(self):
        """Initialize GPIO for HX711."""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.dout_pin, GPIO.IN)
            GPIO.setup(self.sck_pin, GPIO.OUT)
            GPIO.output(self.sck_pin, GPIO.LOW)

            # Set gain by doing a read
            self._read_raw()
        except Exception as e:
            print(f"Failed to initialize HX711: {e}")
            self.simulate = True

    def _is_ready(self) -> bool:
        """Check if HX711 has data ready."""
        if self.simulate:
            return True
        return GPIO.input(self.dout_pin) == GPIO.LOW

    def _read_raw(self) -> int:
        """
        Read raw 24-bit value from HX711.

        Returns:
            Raw ADC value (signed 24-bit)
        """
        if self.simulate:
            # Simulate some noise around the set value
            import random
            base = int(self._sim_thrust * self._scale + self._offset)
            return base + random.randint(-100, 100)

        # Wait for data ready
        timeout = time.time() + 1.0
        while not self._is_ready():
            if time.time() > timeout:
                raise TimeoutError("HX711 not responding")
            time.sleep(0.001)

        # Read 24 bits
        value = 0
        for _ in range(24):
            GPIO.output(self.sck_pin, GPIO.HIGH)
            value = (value << 1) | GPIO.input(self.dout_pin)
            GPIO.output(self.sck_pin, GPIO.LOW)

        # Set gain for next read (extra clock pulses)
        for _ in range(self.gain - 24):
            GPIO.output(self.sck_pin, GPIO.HIGH)
            GPIO.output(self.sck_pin, GPIO.LOW)

        # Convert to signed value
        if value & 0x800000:
            value -= 0x1000000

        return value

    def read_average(self, samples: int = 5) -> int:
        """
        Read averaged raw value.

        Args:
            samples: Number of samples to average

        Returns:
            Averaged raw ADC value
        """
        total = 0
        for _ in range(samples):
            total += self._read_raw()
            time.sleep(0.01)  # Small delay between samples
        return total // samples

    def tare(self, samples: int = 10):
        """
        Tare the scale (set current reading as zero).

        Args:
            samples: Number of samples to average for tare
        """
        print("Taring load cell...")
        self._offset = self.read_average(samples)
        print(f"Tare complete. Offset: {self._offset}")

    def calibrate(self, known_weight_kg: float, samples: int = 10):
        """
        Calibrate with a known weight.

        Args:
            known_weight_kg: Known weight in kg
            samples: Number of samples to average
        """
        print(f"Calibrating with {known_weight_kg} kg weight...")
        raw = self.read_average(samples)
        self._scale = (raw - self._offset) / known_weight_kg
        print(f"Calibration complete. Scale: {self._scale}")

    def read_kg(self, samples: int = 5) -> float:
        """
        Read thrust/weight in kg.

        Args:
            samples: Number of samples to average

        Returns:
            Weight/thrust in kg
        """
        raw = self.read_average(samples)
        return (raw - self._offset) / self._scale if self._scale != 0 else 0.0

    def set_calibration(self, offset: int, scale: float):
        """
        Set calibration values directly.

        Args:
            offset: Tare offset (raw value at zero)
            scale: Conversion factor (raw units per kg)
        """
        self._offset = offset
        self._scale = scale

    def get_calibration(self) -> tuple:
        """
        Get current calibration values.

        Returns:
            Tuple of (offset, scale)
        """
        return self._offset, self._scale

    def set_simulated_thrust(self, thrust_kg: float):
        """
        Set simulated thrust value for testing.

        Args:
            thrust_kg: Simulated thrust in kg
        """
        self._sim_thrust = thrust_kg

    def is_connected(self) -> bool:
        """Check if load cell is connected and responding."""
        if self.simulate:
            return True

        try:
            self._read_raw()
            return True
        except Exception:
            return False

    def cleanup(self):
        """Clean up GPIO resources."""
        if not self.simulate and HARDWARE_AVAILABLE:
            try:
                GPIO.cleanup([self.dout_pin, self.sck_pin])
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False
