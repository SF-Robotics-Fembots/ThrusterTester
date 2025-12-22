"""
PCA9685 PWM Controller interface for thruster control.
Based on Adafruit PCA9685 library usage from ROV reference code.
"""

import time
from typing import Optional

# Hardware imports - will fail gracefully on non-Pi systems
try:
    import board
    import busio
    from adafruit_pca9685 import PCA9685
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False


class PWMController:
    """
    Interface for PCA9685 PWM controller to drive thruster ESCs.

    PWM pulse width conversion:
    - ESCs expect 1000-2000us pulses at 50Hz (20ms period)
    - PCA9685 uses 16-bit duty cycle (0-65535)
    - Formula: duty_cycle = int(pulse_us / 10000 * 65536)
    """

    def __init__(self, address: int = 0x40, frequency_hz: int = 50,
                 channel: int = 0, simulate: bool = False):
        """
        Initialize PWM controller.

        Args:
            address: I2C address of PCA9685 (default 0x40)
            frequency_hz: PWM frequency in Hz (default 50 for ESCs)
            channel: PWM channel to use (0-15)
            simulate: If True, simulate hardware for testing
        """
        self.address = address
        self.frequency_hz = frequency_hz
        self.channel = channel
        self.simulate = simulate or not HARDWARE_AVAILABLE

        self._pca: Optional[PCA9685] = None
        self._current_pwm_us = 1500  # Track current value
        self._is_armed = False

        if not self.simulate:
            self._init_hardware()

    def _init_hardware(self):
        """Initialize PCA9685 hardware."""
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self._pca = PCA9685(i2c, address=self.address)
            self._pca.frequency = self.frequency_hz
        except Exception as e:
            print(f"Failed to initialize PCA9685: {e}")
            self.simulate = True

    def _us_to_duty_cycle(self, pulse_us: int) -> int:
        """
        Convert pulse width in microseconds to PCA9685 duty cycle.

        Formula from ROV reference code:
        duty_cycle = int(pulse_us / 10000 * 65536)

        Args:
            pulse_us: Pulse width in microseconds (typically 1000-2000)

        Returns:
            16-bit duty cycle value (0-65535)
        """
        return int(pulse_us / 10000 * 65536)

    def set_pwm_us(self, pulse_us: int):
        """
        Set PWM pulse width in microseconds.

        Args:
            pulse_us: Pulse width in microseconds
        """
        # Clamp to safe range
        pulse_us = max(1000, min(2000, pulse_us))

        duty_cycle = self._us_to_duty_cycle(pulse_us)

        if not self.simulate:
            try:
                self._pca.channels[self.channel].duty_cycle = duty_cycle
            except Exception as e:
                print(f"Failed to set PWM: {e}")

        self._current_pwm_us = pulse_us

    def get_current_pwm_us(self) -> int:
        """Get the current PWM pulse width in microseconds."""
        return self._current_pwm_us

    def arm(self, neutral_pwm_us: int = 1500):
        """
        Arm the ESC by sending neutral signal.

        Most ESCs require a neutral signal for a period before
        they will respond to throttle commands.

        Args:
            neutral_pwm_us: Neutral PWM value (typically 1500)
        """
        print(f"Arming ESC on channel {self.channel}...")
        self.set_pwm_us(neutral_pwm_us)
        time.sleep(2.0)  # Wait for ESC to arm
        self._is_armed = True
        print("ESC armed.")

    def disarm(self, neutral_pwm_us: int = 1500):
        """
        Disarm the ESC by returning to neutral.

        Args:
            neutral_pwm_us: Neutral PWM value (typically 1500)
        """
        print("Disarming ESC...")
        self.set_pwm_us(neutral_pwm_us)
        self._is_armed = False
        print("ESC disarmed.")

    def emergency_stop(self):
        """Emergency stop - immediately set to neutral."""
        self.set_pwm_us(1500)
        self._is_armed = False

    def is_armed(self) -> bool:
        """Check if ESC is armed."""
        return self._is_armed

    def ramp_to(self, target_us: int, step_us: int = 25, delay_ms: int = 50):
        """
        Gradually ramp PWM to target value for safety.

        Args:
            target_us: Target PWM value in microseconds
            step_us: Step size for ramping
            delay_ms: Delay between steps in milliseconds
        """
        current = self._current_pwm_us

        if target_us > current:
            while current < target_us:
                current = min(current + step_us, target_us)
                self.set_pwm_us(current)
                time.sleep(delay_ms / 1000)
        else:
            while current > target_us:
                current = max(current - step_us, target_us)
                self.set_pwm_us(current)
                time.sleep(delay_ms / 1000)

    def cleanup(self):
        """Clean up resources."""
        if self._pca is not None:
            try:
                # Return to neutral before cleanup
                self.set_pwm_us(1500)
                self._pca.deinit()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False
