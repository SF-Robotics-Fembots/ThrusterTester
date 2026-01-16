"""
Hardware PWM Controller for thruster control using Raspberry Pi GPIO.

Uses the Pi's hardware PWM pins for precise ESC control.
Hardware PWM pins: GPIO 12, 13, 18, 19 (only 2 channels available)
"""

import time
from typing import Optional

# Hardware imports - will fail gracefully on non-Pi systems
try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False


class PWMController:
    """
    Interface for Raspberry Pi hardware PWM to drive thruster ESCs.

    PWM pulse width conversion:
    - ESCs expect 1000-2000us pulses at 50Hz (20ms period)
    - At 50Hz, duty cycle percentage = (pulse_us / 20000) * 100
    - 1500us neutral = 7.5% duty cycle
    """

    # Hardware PWM capable pins on Pi
    HARDWARE_PWM_PINS = [12, 13, 18, 19]

    def __init__(self, gpio_pin: int = 18, frequency_hz: int = 50,
                 simulate: bool = False):
        """
        Initialize hardware PWM controller.

        Args:
            gpio_pin: GPIO pin for PWM output (12, 13, 18, or 19 for hardware PWM)
            frequency_hz: PWM frequency in Hz (default 50 for ESCs)
            simulate: If True, simulate hardware for testing
        """
        self.gpio_pin = gpio_pin
        self.frequency_hz = frequency_hz
        self.simulate = simulate or not HARDWARE_AVAILABLE

        self._pwm: Optional[GPIO.PWM] = None
        self._current_pwm_us = 1500  # Track current value
        self._is_armed = False

        if gpio_pin not in self.HARDWARE_PWM_PINS:
            print(f"Warning: GPIO {gpio_pin} is not a hardware PWM pin. "
                  f"Use one of {self.HARDWARE_PWM_PINS} for best results.")

        if not self.simulate:
            self._init_hardware()

    def _init_hardware(self):
        """Initialize GPIO hardware PWM."""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.OUT)

            # Create PWM instance
            self._pwm = GPIO.PWM(self.gpio_pin, self.frequency_hz)

            # Start at neutral (1500us = 7.5% duty cycle at 50Hz)
            neutral_duty = self._us_to_duty_cycle(1500)
            self._pwm.start(neutral_duty)

        except Exception as e:
            print(f"Failed to initialize hardware PWM: {e}")
            self.simulate = True

    def _us_to_duty_cycle(self, pulse_us: int) -> float:
        """
        Convert pulse width in microseconds to duty cycle percentage.

        At 50Hz (20ms period):
        - 1000us = 5.0% duty cycle
        - 1500us = 7.5% duty cycle
        - 2000us = 10.0% duty cycle

        Args:
            pulse_us: Pulse width in microseconds (typically 1000-2000)

        Returns:
            Duty cycle as percentage (0-100)
        """
        period_us = 1_000_000 / self.frequency_hz  # 20000us at 50Hz
        return (pulse_us / period_us) * 100

    def set_pwm_us(self, pulse_us: int):
        """
        Set PWM pulse width in microseconds.

        Args:
            pulse_us: Pulse width in microseconds
        """
        # Clamp to safe range
        pulse_us = max(1000, min(2000, pulse_us))

        duty_cycle = self._us_to_duty_cycle(pulse_us)

        if not self.simulate and self._pwm:
            try:
                self._pwm.ChangeDutyCycle(duty_cycle)
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
        print(f"Arming ESC on GPIO {self.gpio_pin}...")
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
        """Clean up GPIO resources."""
        if self._pwm is not None:
            try:
                # Return to neutral before cleanup
                self.set_pwm_us(1500)
                self._pwm.stop()
            except Exception:
                pass

        if not self.simulate and HARDWARE_AVAILABLE:
            try:
                GPIO.cleanup(self.gpio_pin)
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False
