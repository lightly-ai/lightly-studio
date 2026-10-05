from __future__ import annotations

from pytest_mock import MockerFixture

from lightly_studio.core.mcap.reader import calibration


def test_dynamic_edges_until__skips_blank_frame_names(mocker: MockerFixture) -> None:
    messages = [
        {"transforms": [{"header": {"frame_id": " "}, "child_frame_id": "base_link"}]},
        {"transforms": [{"header": {"frame_id": "map"}, "child_frame_id": ""}]},
        {"transforms": [{"header": {"frame_id": "map"}, "child_frame_id": "base_link"}]},
        {"transforms": [{"header": {"frame_id": "odom"}, "child_frame_id": "map"}]},
    ]
    mcap_reader = mocker.MagicMock()
    mcap_reader.iter_decoded_messages.return_value = [
        (None, None, None, message) for message in messages
    ]

    edges = calibration.dynamic_edges_until(
        mcap_reader=mcap_reader,
        path="recording.mcap",
        topic="/tf",
        frame_ids=["map", "base_link"],
    )

    assert edges == [("map", "base_link")]
