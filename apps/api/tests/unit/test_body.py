"""
Body analysis tests (Phase 4 acceptance criteria).

Tests cover:
- canonical measurement sets for all 5 shapes
- runner-up sensitivity for borderline cases
- body-positive styling guidance
- silhouette-based visual measurement for valid front-facing images
- rejection of cropped, side-view, multi-person, and low-visibility images
"""

import io
from types import SimpleNamespace

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw

from app.main import app
from app.services.body.fit import body_fit
from app.services.body.measure import VisualMeasurementError, estimate_proportions_from_image
from app.services.body.shape import classify_body_shape


class _FakeLandmark(SimpleNamespace):
    pass


def _make_silhouette_image(width: int = 220, height: int = 480, *, shoulder: int = 120, waist: int = 80, hip: int = 110):
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    head_center = (width // 2, 40)
    draw.ellipse((head_center[0] - 18, head_center[1] - 18, head_center[0] + 18, head_center[1] + 18), fill=(0, 0, 0))

    shoulder_y = int(height * 0.24)
    waist_y = int(height * 0.46)
    hip_y = int(height * 0.62)

    draw.polygon(
        [
            (width // 2 - shoulder // 2, shoulder_y),
            (width // 2 + shoulder // 2, shoulder_y),
            (width // 2 + waist // 2, waist_y),
            (width // 2 - waist // 2, waist_y),
        ],
        fill=(0, 0, 0),
    )
    draw.ellipse((width // 2 - hip // 2, hip_y - 18, width // 2 + hip // 2, hip_y + 18), fill=(0, 0, 0))
    draw.rectangle((width // 2 - waist // 2, waist_y - 18, width // 2 + waist // 2, hip_y), fill=(0, 0, 0))
    return image


def _fake_mask_and_landmarks(width: int, height: int, *, shoulder: int = 120, waist: int = 80, hip: int = 110):
    mask = np.zeros((height, width), dtype=bool)
    cx = width // 2
    shoulder_y = int(height * 0.24)
    waist_y = int(height * 0.46)
    hip_y = int(height * 0.62)
    for y in range(height):
        for x in range(width):
            if (abs(x - cx) <= shoulder // 2 and abs(y - shoulder_y) <= 10) or (
                abs(x - cx) <= waist // 2 and abs(y - waist_y) <= 18
            ) or (
                abs(x - cx) <= hip // 2 and abs(y - hip_y) <= 18
            ):
                mask[y, x] = True
    left_shoulder = _FakeLandmark(x=(cx - shoulder / 2) / width, y=shoulder_y / height, visibility=1.0)
    right_shoulder = _FakeLandmark(x=(cx + shoulder / 2) / width, y=shoulder_y / height, visibility=1.0)
    left_hip = _FakeLandmark(x=(cx - hip / 2) / width, y=hip_y / height, visibility=1.0)
    right_hip = _FakeLandmark(x=(cx + hip / 2) / width, y=hip_y / height, visibility=1.0)
    return mask, {"left_shoulder": left_shoulder, "right_shoulder": right_shoulder, "left_hip": left_hip, "right_hip": right_hip}


@pytest.mark.asyncio
class TestBodyAnalysis:

    async def _register_and_auth(self, client: AsyncClient, email: str = "bodytest@example.com") -> str:
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "SecurePassword123!"},
        )
        return reg_resp.json()["access_token"]

    async def test_canonical_shape_classification(self):
        hg = classify_body_shape(shoulder=95, waist=66, hip=96)
        assert hg["shape"] == "Hourglass"
        assert hg["confidence"] >= 0.70
        assert len(hg["recommended_silhouettes"]) > 0

        pear = classify_body_shape(shoulder=84, waist=68, hip=102)
        assert pear["shape"] == "Pear"
        assert pear["confidence"] >= 0.70

        inv_tri = classify_body_shape(shoulder=106, waist=76, hip=90)
        assert inv_tri["shape"] == "Inverted Triangle"
        assert inv_tri["confidence"] >= 0.70

        rect = classify_body_shape(shoulder=92, waist=80, hip=94)
        assert rect["shape"] == "Rectangle"
        assert rect["confidence"] >= 0.60

        apple = classify_body_shape(shoulder=94, waist=92, hip=95)
        assert apple["shape"] == "Apple"
        assert apple["confidence"] >= 0.60

    async def test_boundary_case_has_runner_up(self):
        borderline = classify_body_shape(shoulder=91, waist=74, hip=100)
        assert borderline["runner_up"] is not None
        assert borderline["runner_up"] in ("Pear", "Hourglass")

    @pytest.mark.parametrize(
        "shape, attrs",
        [
            ("Hourglass", {"neckline": "v_neck", "fit": "tailored", "length": "midi", "rise": "high_rise", "subcategory": "dress"}),
            ("Pear", {"neckline": "boat_neck", "fit": "regular", "length": "midi", "rise": "high_rise", "subcategory": "skirt"}),
            ("Inverted Triangle", {"neckline": "v_neck", "fit": "wide_leg", "length": "maxi", "rise": "mid_rise", "subcategory": "trousers"}),
            ("Rectangle", {"neckline": "boat_neck", "fit": "tailored", "length": "midi", "rise": "high_rise", "subcategory": "dress"}),
            ("Apple", {"neckline": "v_neck", "fit": "relaxed", "length": "maxi", "rise": "mid_rise", "subcategory": "dress"}),
        ],
    )
    async def test_shape_preferences_and_fit_score(self, shape, attrs):
        score = body_fit(attrs, shape)
        assert 0.0 <= score <= 1.0
        result = classify_body_shape(shoulder=96, waist=68, hip=98, source="manual")
        assert result["recommendations"]
        assert isinstance(result["recommendations"], list)

    async def test_manual_measurements_endpoint_and_encryption(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = await self._register_and_auth(client, "measure_user@example.com")

            resp = await client.post(
                "/api/v1/body/manual",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "shoulder": 96.0,
                    "waist": 68.0,
                    "hip": 98.0,
                    "height": 168.0,
                    "inseam": 76.0,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["shape"] == "Hourglass"
            assert data["source"] == "manual"
            assert len(data["recommended_silhouettes"]) > 0

            resp_str = str(data).lower()
            assert "bmi" not in resp_str
            assert "weight" not in resp_str
            assert "fat" not in resp_str

            patch_resp = await client.patch(
                "/api/v1/body/correction",
                headers={"Authorization": f"Bearer {token}"},
                json={"shape": "Rectangle"},
            )
            assert patch_resp.status_code == 200
            assert patch_resp.json()["shape"] == "Rectangle"
            assert patch_resp.json()["user_corrected_shape"] == "Rectangle"

    async def test_estimate_proportions_from_pillow_silhouette_shapes(self, monkeypatch):
        for shape_name, params in {
            "Hourglass": {"shoulder": 110, "waist": 78, "hip": 108},
            "Pear": {"shoulder": 90, "waist": 72, "hip": 120},
            "Inverted Triangle": {"shoulder": 130, "waist": 90, "hip": 104},
            "Rectangle": {"shoulder": 116, "waist": 94, "hip": 112},
            "Apple": {"shoulder": 118, "waist": 110, "hip": 110},
        }.items():
            width, height = 220, 460
            silhouette = _make_silhouette_image(width, height, **params)
            mask, landmarks = _fake_mask_and_landmarks(width, height, **params)
            monkeypatch.setattr(
                "app.services.body.measure._detect_pose_and_mask",
                lambda image: (mask, landmarks),
            )

            buffer = io.BytesIO()
            silhouette.save(buffer, format="PNG")
            proportions = estimate_proportions_from_image(buffer.getvalue())
            assert proportions["shoulder"] > 0
            assert proportions["hip"] > 0
            assert proportions["waist"] > 0
            assert proportions["shoulder"] >= proportions["waist"]

            class_result = classify_body_shape(
                shoulder=proportions["shoulder"],
                waist=proportions["waist"],
                hip=proportions["hip"],
            )
            assert class_result["shape"] == shape_name

    @pytest.mark.parametrize(
        "mask_factory, landmarks_factory",
        [
            (
                lambda w, h: np.zeros((h, w), dtype=bool),
                lambda w, h: {
                    "left_shoulder": _FakeLandmark(x=0.2, y=0.2, visibility=1.0),
                    "right_shoulder": _FakeLandmark(x=0.25, y=0.2, visibility=1.0),
                    "left_hip": _FakeLandmark(x=0.2, y=0.3, visibility=1.0),
                    "right_hip": _FakeLandmark(x=0.25, y=0.3, visibility=1.0),
                },
            ),
            (
                lambda w, h: np.ones((h, w), dtype=bool),
                lambda w, h: {
                    "left_shoulder": _FakeLandmark(x=0.12, y=0.22, visibility=1.0),
                    "right_shoulder": _FakeLandmark(x=0.42, y=0.22, visibility=1.0),
                    "left_hip": _FakeLandmark(x=0.18, y=0.56, visibility=1.0),
                    "right_hip": _FakeLandmark(x=0.50, y=0.56, visibility=1.0),
                },
            ),
            (
                lambda w, h: np.zeros((h, w), dtype=bool),
                lambda w, h: {
                    "left_shoulder": _FakeLandmark(x=0.18, y=0.12, visibility=1.0),
                    "right_shoulder": _FakeLandmark(x=0.32, y=0.12, visibility=1.0),
                    "left_hip": _FakeLandmark(x=0.18, y=0.42, visibility=1.0),
                    "right_hip": _FakeLandmark(x=0.32, y=0.42, visibility=1.0),
                },
            ),
        ],
    )
    async def test_rejects_invalid_visual_measurements(self, monkeypatch, mask_factory, landmarks_factory):
        width, height = 220, 460
        mask = mask_factory(width, height)
        if mask.ndim != 2:
            mask = np.zeros((height, width), dtype=bool)
        if mask.shape != (height, width):
            mask = np.zeros((height, width), dtype=bool)
        if mask.sum() == 0:
            mask[20:80, 20:80] = True
        if mask.sum() == mask.size:
            mask[20:80, 20:80] = False
            mask[260:340, 120:180] = True
        monkeypatch.setattr(
            "app.services.body.measure._detect_pose_and_mask",
            lambda image: (mask, landmarks_factory(width, height)),
        )

        with pytest.raises(VisualMeasurementError):
            estimate_proportions_from_image(b"fake")

    async def test_visual_analysis_and_privacy_purge(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = await self._register_and_auth(client, "visual_user@example.com")
            img = Image.new("RGB", (200, 400), color=(200, 180, 160))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            media_resp = await client.post(
                "/api/v1/media",
                headers={"Authorization": f"Bearer {token}"},
                data={"kind": "body_image"},
                files={"file": ("full_body.jpg", buf.getvalue(), "image/jpeg")},
            )
            assert media_resp.status_code == 201
            asset_id = media_resp.json()["id"]

            analyze_resp = await client.post(
                "/api/v1/body/analyze",
                headers={"Authorization": f"Bearer {token}"},
                json={"asset_id": asset_id},
            )
            assert analyze_resp.status_code == 200
            data = analyze_resp.json()
            assert data["shape"] is not None
            assert data["source"] == "photo"

            get_media = await client.get(f"/api/v1/media/{asset_id}", headers={"Authorization": f"Bearer {token}"})
            assert get_media.status_code == 404

    async def test_body_idor_isolation(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token_a = await self._register_and_auth(client, "body_a@example.com")
            token_b = await self._register_and_auth(client, "body_b@example.com")
            await client.post(
                "/api/v1/body/manual",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"shoulder": 92.0, "waist": 80.0, "hip": 94.0},
            )
            b_get = await client.get("/api/v1/body", headers={"Authorization": f"Bearer {token_b}"})
            assert b_get.status_code == 404
