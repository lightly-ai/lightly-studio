"""Duplicate samples/embeddings in a DuckDB to create a larger benchmark dataset.

Hardcoded params below. This keeps a single dataset per DB and appends duplicated
samples into the same collection(s).
"""

from __future__ import annotations

import random
import shutil
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - optional dependency
    def tqdm(iterable=None, total=None, desc=None):
        if iterable is None:
            class _TqdmNoop:
                def update(self, _n=1):
                    return None
                def close(self):
                    return None
            return _TqdmNoop()
        return iterable

from sqlmodel import Session, col, create_engine, select

import lightly_studio.api.db_tables  # noqa: F401
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers.collection_resolver.deep_copy import _copy_with_updates

INPUT_DB_PATH = "/Users/malteebnerlightly/Documents/GitHub/lightly-studio/benchmark_embedding_loading/lexica_benchmark.db"
OUTPUT_DB_PATH = "/Users/malteebnerlightly/Documents/GitHub/lightly-studio/benchmark_embedding_loading/lexica_benchmark_x10.db"
MULTIPLIER = 10
BATCH_SIZE = 1000
NOISE_SCALE = 1e-3


def _cleanup_output_db(db_path: Path) -> None:
    for suffix in ("", ".wal", ".tmp"):
        path = Path(f"{db_path}{suffix}")
        if path.exists():
            path.unlink()


def _add_noise(values: list[float]) -> list[float]:
    rand = random.random
    scale = NOISE_SCALE
    return [v + (rand() - 0.5) * scale for v in values]


def _chunks(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def main() -> None:
    input_path = Path(INPUT_DB_PATH)
    output_path = Path(OUTPUT_DB_PATH)

    if input_path.resolve() == output_path.resolve():
        raise ValueError("INPUT_DB_PATH and OUTPUT_DB_PATH must be different.")

    if not input_path.exists():
        raise FileNotFoundError(f"Input DB not found: {input_path}")

    _cleanup_output_db(output_path)
    shutil.copyfile(input_path, output_path)

    engine = create_engine(f"duckdb:///{output_path}")

    with Session(engine) as session:
        base_sample_ids = list(
            session.exec(select(SampleTable.sample_id).order_by(col(SampleTable.sample_id))).all()
        )

        if not base_sample_ids:
            print("No samples found in input DB.")
            return

        target_total = len(base_sample_ids) * MULTIPLIER
        print(f"Base samples: {len(base_sample_ids)} -> Target samples: {target_total}")

        total_new = len(base_sample_ids) * (MULTIPLIER - 1)
        progress = tqdm(total=total_new, desc="Duplicating samples")

        for batch_ids in _chunks(base_sample_ids, BATCH_SIZE):
            samples = session.exec(
                select(SampleTable).where(col(SampleTable.sample_id).in_(batch_ids))
            ).all()
            images = session.exec(
                select(ImageTable).where(col(ImageTable.sample_id).in_(batch_ids))
            ).all()
            embeddings = session.exec(
                select(SampleEmbeddingTable).where(col(SampleEmbeddingTable.sample_id).in_(batch_ids))
            ).all()

            image_by_sample = {image.sample_id: image for image in images}
            embeddings_by_sample: dict = defaultdict(list)
            for embedding in embeddings:
                embeddings_by_sample[embedding.sample_id].append(embedding)

            for rep in range(MULTIPLIER - 1):
                new_samples: list[SampleTable] = []
                new_images: list[ImageTable] = []
                new_embeddings: list[SampleEmbeddingTable] = []

                for sample in samples:
                    new_id = uuid4()
                    new_samples.append(
                        _copy_with_updates(
                            sample,
                            {
                                "sample_id": new_id,
                                "collection_id": sample.collection_id,
                            },
                        )
                    )

                    image = image_by_sample.get(sample.sample_id)
                    if image is not None:
                        file_name = image.file_name
                        if not file_name:
                            if image.file_path_abs:
                                file_name = Path(image.file_path_abs).name
                            else:
                                file_name = f"{new_id}.jpg"
                        new_images.append(
                            ImageTable(
                                file_name=file_name,
                                width=image.width,
                                height=image.height,
                                file_path_abs=image.file_path_abs,
                                sample_id=new_id,
                            )
                        )

                    for embedding in embeddings_by_sample.get(sample.sample_id, []):
                        new_embeddings.append(
                            SampleEmbeddingTable(
                                sample_id=new_id,
                                embedding_model_id=embedding.embedding_model_id,
                                embedding=_add_noise(embedding.embedding),
                            )
                        )

                session.add_all(new_samples)
                session.add_all(new_images)
                session.add_all(new_embeddings)
                session.commit()
                progress.update(len(samples))

        final_count = session.exec(select(SampleTable.sample_id)).all()
        progress.close()
        print(f"Final samples: {len(final_count)}")
        print("Done.")


if __name__ == "__main__":
    main()
