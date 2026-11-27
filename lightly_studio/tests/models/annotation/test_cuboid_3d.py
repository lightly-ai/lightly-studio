"""Tests for Cuboid3DCreate validation."""

from __future__ import annotations

import math

import pytest

from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate


class TestCuboid3DCreate:
    def test_init__valid(self) -> None:
        cuboid = Cuboid3DCreate(
            frame_id="odom",
            px=1.0,
            py=0.0,
            pz=0.5,
            qx=0.0,
            qy=0.0,
            qz=0.0,
            qw=1.0,
            sx=2.0,
            sy=1.0,
            sz=1.5,
        )
        assert cuboid.frame_id == "odom"
        assert cuboid.interpolated is False

    def test_init__non_positive_sx(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            Cuboid3DCreate(
                frame_id="odom",
                px=0.0,
                py=0.0,
                pz=0.0,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                sx=0.0,
                sy=1.0,
                sz=1.0,
            )

    def test_init__non_positive_sy(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            Cuboid3DCreate(
                frame_id="odom",
                px=0.0,
                py=0.0,
                pz=0.0,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                sx=1.0,
                sy=-0.5,
                sz=1.0,
            )

    def test_init__non_positive_sz(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            Cuboid3DCreate(
                frame_id="odom",
                px=0.0,
                py=0.0,
                pz=0.0,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                sx=1.0,
                sy=1.0,
                sz=0.0,
            )

    def test_init__non_unit_quaternion(self) -> None:
        # norm = sqrt(1 + 0 + 0 + 1) = sqrt(2) ≠ 1
        with pytest.raises(ValueError, match="unit quaternion"):
            Cuboid3DCreate(
                frame_id="odom",
                px=0.0,
                py=0.0,
                pz=0.0,
                qx=1.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                sx=1.0,
                sy=1.0,
                sz=1.0,
            )

    def test_init__non_unit_quaternion__zero(self) -> None:
        with pytest.raises(ValueError, match="unit quaternion"):
            Cuboid3DCreate(
                frame_id="odom",
                px=0.0,
                py=0.0,
                pz=0.0,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=0.0,
                sx=1.0,
                sy=1.0,
                sz=1.0,
            )

    def test_init__non_finite_position(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            Cuboid3DCreate(
                frame_id="odom",
                px=math.nan,
                py=0.0,
                pz=0.0,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                sx=1.0,
                sy=1.0,
                sz=1.0,
            )

    def test_init__non_finite_size(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            Cuboid3DCreate(
                frame_id="odom",
                px=0.0,
                py=0.0,
                pz=0.0,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                sx=math.inf,
                sy=1.0,
                sz=1.0,
            )

    def test_init__non_unit_quaternion__very_large_component(self) -> None:
        """A finite but very large quaternion component is rejected as non-unit."""
        with pytest.raises(ValueError, match="unit quaternion"):
            Cuboid3DCreate(
                frame_id="odom",
                px=0.0,
                py=0.0,
                pz=0.0,
                qx=1e308,
                qy=0.0,
                qz=0.0,
                qw=0.0,
                sx=1.0,
                sy=1.0,
                sz=1.0,
            )

    def test_init__unit_quaternion_near_boundary(self) -> None:
        """Quaternion within floating-point tolerance (1e-6) is accepted."""
        Cuboid3DCreate(
            frame_id="odom",
            px=0.0,
            py=0.0,
            pz=0.0,
            qx=0.0,
            qy=0.0,
            qz=0.0,
            qw=1.0 + 5e-7,
            sx=1.0,
            sy=1.0,
            sz=1.0,
        )
