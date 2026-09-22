"""Run the camera demo: Camera Station, LightlyStudio, LightlyTrain and MQTT.

The demo covers the whole loop on one machine:

1. Watch a camera feed (RTSP, webcam or video file) on the Camera Station page.
2. Bookmark interesting frames. They become image samples in LightlyStudio.
3. Group and label the frames in LightlyStudio.
4. Train a detector with LightlyTrain from the LightlyStudio "Plugins" menu.
5. Review the model in the LightlyStudio Eval tab.
6. Deploy the model on the live feed and send the detections to MQTT or a Python script.

Example:
    python -m lightly_studio.examples.camera_plugins_demo.run_camera_demo \
        --source rtsp://127.0.0.1:8554/cam --mqtt-host localhost
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import lightly_studio as ls
from lightly_studio.database import db_manager
from lightly_studio.examples.camera_plugins_demo import demo_app, station
from lightly_studio.examples.camera_plugins_demo.demo_app import DemoSettings
from lightly_studio.examples.camera_plugins_demo.operators import build_operators
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.resolvers import image_resolver

logger = logging.getLogger(__name__)

_FIRST_FRAME_TIMEOUT_S = 20.0


def main() -> None:
    """Start the camera demo and serve the LightlyStudio GUI until interrupted."""
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    data_dir = args.data_dir.expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    db_manager.connect(db_file=str(data_dir / "camera_demo.db"), cleanup_existing=args.reset)
    dataset = ls.ImageDataset.load_or_create(name=args.dataset_name)

    settings = DemoSettings(
        source=args.source,
        data_dir=data_dir,
        dataset_name=args.dataset_name,
        studio_url=f"http://localhost:{args.port}",
        station_port=args.station_port,
        embed=args.embed,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        mqtt_topic=args.mqtt_topic,
        hook_script=args.hook_script,
        default_model=args.model,
        default_steps=args.steps,
    )
    demo = demo_app.build_demo(
        settings=settings,
        dataset_id=dataset.dataset_id,
        collection_id=dataset.collection_id,
    )

    demo.camera.start()
    demo.dispatcher.start()
    _seed_first_frame(demo=demo)

    for operator in build_operators(demo=demo):
        operator_registry.register(operator=operator)

    station.serve_in_background(demo=demo, port=args.station_port)
    _print_banner(demo=demo, studio_port=args.port)

    try:
        ls.start_gui(port=args.port)
    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        demo.shutdown()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default="0",
        help="Camera source: an RTSP or HTTP URL, a webcam index such as 0, or a video file.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("camera_demo_data"),
        help="Directory for the database, the bookmarked frames and the training runs.",
    )
    parser.add_argument("--dataset-name", default="camera", help="LightlyStudio dataset name.")
    parser.add_argument("--port", type=int, default=8001, help="Port of the LightlyStudio GUI.")
    parser.add_argument(
        "--station-port", type=int, default=8002, help="Port of the Camera Station page."
    )
    parser.add_argument("--mqtt-host", default=None, help="MQTT broker host. Off when not set.")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port.")
    parser.add_argument("--mqtt-topic", default="lightly/camera", help="MQTT topic prefix.")
    parser.add_argument(
        "--hook-script",
        type=Path,
        default=None,
        help="Python file with on_detections(message) and on_event(message) functions.",
    )
    parser.add_argument(
        "--model", default=demo_app.DEFAULT_MODEL, help="LightlyTrain model to fine-tune."
    )
    parser.add_argument("--steps", type=int, default=40, help="Default number of training steps.")
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Embed every bookmarked frame so similarity search and the embedding view work.",
    )
    parser.add_argument(
        "--reset", action="store_true", help="Delete the existing database before starting."
    )
    return parser.parse_args()


def _seed_first_frame(demo: demo_app.CameraDemo) -> None:
    """Make sure the dataset holds at least one image, which the GUI requires."""
    with db_manager.session() as session:
        result = image_resolver.get_all_by_collection_id(
            session=session, collection_id=demo.collection_id
        )
        if result.total_count > 0:
            logger.info("Dataset holds %s images.", result.total_count)
            return

    logger.info("Empty dataset. Waiting for the first camera frame.")
    frame = demo.camera.wait_for_frame(after_index=-1, timeout=_FIRST_FRAME_TIMEOUT_S)
    if frame is None:
        raise SystemExit(
            f"No frame from '{demo.settings.source}' within {_FIRST_FRAME_TIMEOUT_S:.0f}s. "
            "Check the camera source, or grant camera access to your terminal for a webcam."
        )
    demo.bookmark(tags=[])


def _print_banner(demo: demo_app.CameraDemo, studio_port: int) -> None:
    print(
        "\n".join(
            [
                "",
                "  LightlyStudio camera demo",
                f"  Camera Station : {demo.station_url}",
                f"  LightlyStudio  : http://localhost:{studio_port}",
                f"  Camera source  : {demo.settings.source}",
                f"  Data directory : {demo.settings.data_dir}",
                "",
            ]
        )
    )


if __name__ == "__main__":
    main()
