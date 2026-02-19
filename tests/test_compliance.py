"""Unit tests for compliance checks."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.compliance import check_layout
from src.models import Layout, ParkingSpace


def test_rotated_space_boundary_violation_detected():
    layout = Layout(
        name="rotated-boundary",
        lot_width=20,
        lot_length=20,
        boundary=[(0, 0), (20, 0), (20, 20), (0, 20)],
        spaces=[
            ParkingSpace(
                id=1,
                type="truck",
                x=12,
                y=12,
                length=10,
                width=3.5,
                rotation=45,
            )
        ],
    )

    report = check_layout(layout)
    assert report.errors > 0
    assert any(v.category == "boundary" for v in report.violations)


def test_spacing_warning_for_nearby_rotated_spaces():
    layout = Layout(
        name="spacing-rotated",
        lot_width=60,
        lot_length=60,
        boundary=[(0, 0), (60, 0), (60, 60), (0, 60)],
        spaces=[
            ParkingSpace(id=1, type="tractor", x=10, y=10, length=8.5, width=3.5, rotation=30),
            ParkingSpace(id=2, type="tractor", x=18, y=12, length=8.5, width=3.5, rotation=0),
        ],
    )

    report = check_layout(layout)
    assert any(v.category == "spacing" for v in report.violations)
