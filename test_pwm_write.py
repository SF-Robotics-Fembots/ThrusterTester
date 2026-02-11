#!/usr/bin/env python3
"""Test PWM on GPIO18 using gpio_write for Pi 5."""

import lgpio
import time
import threading

CHIP = 4
GPIO = 18
FREQ = 50
PERIOD_S = 1.0 / FREQ  # 20ms

chip = lgpio.gpiochip_open(CHIP)
lgpio.gpio_claim_output(chip, GPIO, 0)

pulse_us = 1500
running = True

def pwm_loop():
    while running:
        high_s = pulse_us / 1000000.0
        low_s = PERIOD_S - high_s
        lgpio.gpio_write(chip, GPIO, 1)
        time.sleep(high_s)
        lgpio.gpio_write(chip, GPIO, 0)
        time.sleep(low_s)

thread = threading.Thread(target=pwm_loop, daemon=True)
thread.start()

print(f"PWM running on GPIO{GPIO} at {FREQ}Hz, {pulse_us}us")
print("Check scope. Press Ctrl+C to stop.")

try:
    time.sleep(10)
except KeyboardInterrupt:
    pass

running = False
time.sleep(0.05)
lgpio.gpio_write(chip, GPIO, 0)
lgpio.gpiochip_close(chip)
print("Done")
