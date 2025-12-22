"""
Deadband analyzer for finding the thruster "off" zone.

The deadband is the PWM range around neutral (typically 1500us) where
the thruster produces no significant thrust.
"""

from typing import List, Tuple
from ..data.models import TestPoint, DeadbandResult


def analyze_deadband(test_points: List[TestPoint],
                     neutral_pwm_us: int = 1500,
                     thrust_threshold_kg: float = 0.01,
                     step_resolution_us: int = 5) -> DeadbandResult:
    """
    Analyze test points to find the deadband (off zone).

    The algorithm finds the PWM range where thrust is below the noise threshold,
    rounding to the specified resolution.

    Args:
        test_points: List of TestPoint measurements
        neutral_pwm_us: Expected neutral PWM value
        thrust_threshold_kg: Minimum thrust to consider "on" (default 0.01 kg)
        step_resolution_us: Round deadband bounds to this resolution (default 5us)

    Returns:
        DeadbandResult with min/max off values, midpoint, and range
    """
    if not test_points:
        return DeadbandResult(
            min_off_pwm_us=neutral_pwm_us,
            max_off_pwm_us=neutral_pwm_us,
            midpoint_pwm_us=float(neutral_pwm_us),
            range_us=0
        )

    # Sort points by PWM value
    sorted_points = sorted(test_points, key=lambda p: p.pwm_us)

    # Find points around neutral
    min_off = neutral_pwm_us
    max_off = neutral_pwm_us

    # Scan downward from neutral to find lower bound
    for point in reversed(sorted_points):
        if point.pwm_us > neutral_pwm_us:
            continue
        if abs(point.thrust_kg) < thrust_threshold_kg:
            min_off = point.pwm_us
        else:
            break

    # Scan upward from neutral to find upper bound
    for point in sorted_points:
        if point.pwm_us < neutral_pwm_us:
            continue
        if abs(point.thrust_kg) < thrust_threshold_kg:
            max_off = point.pwm_us
        else:
            break

    # Round to resolution
    min_off = round_to_resolution(min_off, step_resolution_us, round_down=True)
    max_off = round_to_resolution(max_off, step_resolution_us, round_down=False)

    # Calculate midpoint and range
    midpoint = (min_off + max_off) / 2.0
    range_us = max_off - min_off

    return DeadbandResult(
        min_off_pwm_us=min_off,
        max_off_pwm_us=max_off,
        midpoint_pwm_us=midpoint,
        range_us=range_us
    )


def round_to_resolution(value: int, resolution: int, round_down: bool = True) -> int:
    """
    Round a value to the nearest resolution boundary.

    Args:
        value: Value to round
        resolution: Resolution to round to
        round_down: If True, round toward zero; if False, round away from zero

    Returns:
        Rounded value
    """
    if round_down:
        return (value // resolution) * resolution
    else:
        return ((value + resolution - 1) // resolution) * resolution


def find_thrust_onset_points(test_points: List[TestPoint],
                             neutral_pwm_us: int = 1500,
                             thrust_threshold_kg: float = 0.01) -> Tuple[int, int]:
    """
    Find the exact PWM values where thrust first becomes significant.

    Args:
        test_points: List of TestPoint measurements
        neutral_pwm_us: Expected neutral PWM value
        thrust_threshold_kg: Minimum thrust to consider "on"

    Returns:
        Tuple of (forward_onset_pwm, reverse_onset_pwm)
    """
    sorted_points = sorted(test_points, key=lambda p: p.pwm_us)

    forward_onset = None
    reverse_onset = None

    # Find forward thrust onset (above neutral)
    for point in sorted_points:
        if point.pwm_us > neutral_pwm_us and point.thrust_kg > thrust_threshold_kg:
            forward_onset = point.pwm_us
            break

    # Find reverse thrust onset (below neutral)
    for point in reversed(sorted_points):
        if point.pwm_us < neutral_pwm_us and point.thrust_kg < -thrust_threshold_kg:
            reverse_onset = point.pwm_us
            break

    return (
        forward_onset or neutral_pwm_us,
        reverse_onset or neutral_pwm_us
    )
