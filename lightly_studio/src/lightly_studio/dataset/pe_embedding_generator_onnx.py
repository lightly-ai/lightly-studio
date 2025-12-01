"""PE embedding generator."""

from __future__ import annotations

import copy
from typing import Callable
from uuid import UUID

import fsspec
import numpy as np
import onnxruntime as ort
import torch
from numpy.typing import NDArray
from PIL import Image
from torch.nn import functional as F
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.vendor.pe.vision_encoder import pe, transforms

from .embedding_generator import EmbeddingGenerator

MODEL_NAME = "PE-Core-T16-384"
MAX_BATCH_SIZE: int = 16
EMBEDDING_DIMENSION: int = 512

class PEVision(torch.nn.Module):
    def __init__(
        self,
        CLIP_model,
    ):
        super().__init__()
        self.model = CLIP_model.visual
        self.image_size = CLIP_model.image_size
        self.logit_scale = CLIP_model.logit_scale

    def forward(self, image):
        x = self.model(image)
        return F.normalize(x, dim=-1)

class PEText(torch.nn.Module):
    def __init__(
        self,
        CLIP_model,
    ):
        super().__init__()
        self.model = copy.deepcopy(CLIP_model)
        delattr(self.model, "visual")

    def forward(self, text):
        return self.model.encode_text(text, normalize=True)

# Dataset for efficient batched image loading and preprocessing
class _ImageFileDataset(Dataset[torch.Tensor]):
    """Dataset wrapping image file paths and a preprocess function."""

    def __init__(
        self,
        filepaths: list[str],
        preprocess: Callable[[Image.Image], torch.Tensor],
    ) -> None:
        self.filepaths = filepaths
        self.preprocess = preprocess

    def __len__(self) -> int:
        return len(self.filepaths)

    def __getitem__(self, idx: int) -> torch.Tensor:
        with fsspec.open(self.filepaths[idx], "rb") as file:
            image = Image.open(file).convert("RGB")
            return self.preprocess(image).half()


class PEEmbeddingGenerator(EmbeddingGenerator):
    """PE embedding model."""

    def __init__(self) -> None:
        """Initialize the PE embedding model.

        This method loads the PE model and its tokenizer. The model
        checkpoint is downloaded and cached locally for future use.
        """
        CLIP_model = pe.CLIP.from_config(MODEL_NAME, pretrained=True).half()
        model_vision = PEVision(CLIP_model=CLIP_model)
        model_text = PEText(CLIP_model=CLIP_model)
        example_inputs = (torch.randn(MAX_BATCH_SIZE, 3, CLIP_model.image_size, CLIP_model.image_size).half(),)
        torch.onnx.export(
            model=model_vision,
            args=example_inputs,
            f="visual_PE.onnx",
            input_names = ['image'],   # the model's input name
            output_names = ['embedding'], # the model's output name
            dynamic_axes={"image": {0: "batch_size"}, "embedding": {0: "batch_size"}})
        self._model_vision = ort.InferenceSession("visual_PE.onnx")

        example_inputs = (torch.rand(1, CLIP_model.context_length).long(),)
        torch.onnx.export(
            model=model_text,
            args=example_inputs,
            f="textual_PE.onnx",
            input_names = ['text'],   # the model's input name
            output_names = ['embedding_text'], # the model's output name
            dynamic_axes={"text": {0: "batch_size"}, "embedding_text": {0: "batch_size"}})
        self._model_text = ort.InferenceSession("textual_PE.onnx")

        self._preprocess = transforms.get_image_transform(CLIP_model.image_size)
        self._tokenizer = transforms.get_text_tokenizer(CLIP_model.context_length)

        self._model_hash = "abc"

    def get_embedding_model_input(self, dataset_id: UUID) -> EmbeddingModelCreate:
        """Generate an EmbeddingModelCreate instance.

        Args:
            dataset_id: The ID of the dataset.

        Returns:
            An EmbeddingModelCreate instance with the model details.
        """
        return EmbeddingModelCreate(
            name=MODEL_NAME,
            embedding_model_hash=self._model_hash,
            embedding_dimension=EMBEDDING_DIMENSION,
            dataset_id=dataset_id,
        )

    def embed_text(self, text: str) -> list[float]:
        """Embed a text with PE.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the generated embedding.
        """
        tokenized = self._tokenizer([text]).long().cpu().numpy()
        with torch.no_grad():
            embedding = self._model_text.run(None, {"text":tokenized})[0]
            # Convert embedding to list of floats.
            embedding_list: list[float] = embedding.flatten().tolist()
        return embedding_list

    def embed_images(self, filepaths: list[str]) -> NDArray[np.float32]:
        """Embed images with PE.

        Args:
            filepaths: A list of file paths to the images to embed.

        Returns:
            A numpy array representing the generated embeddings
            in the same order as the input file paths.
        """
        dataset = _ImageFileDataset(filepaths, self._preprocess)

        # To avoid issues with db locking and multiprocessing we set the
        # number of workers to 0 (no multiprocessing). The DataLoader is still
        # very useful for batching and async prefetching of images.
        loader = DataLoader(
            dataset,
            batch_size=MAX_BATCH_SIZE,
            num_workers=0,  # must be 0 to avoid multiprocessing issues
        )
        total_images = len(filepaths)
        if not total_images:
            return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)

        embeddings = np.empty((total_images, EMBEDDING_DIMENSION), dtype=np.float32)
        position = 0
        with tqdm(
            total=total_images, desc="Generating embeddings", unit=" images"
        ) as progress_bar, torch.no_grad():
            for images_tensor in loader:
                imgs = images_tensor.to("cpu", non_blocking=True).cpu().numpy()
                batch_embeddings = self._model_vision.run(None, {"image":imgs})
                embeddings[position:position+MAX_BATCH_SIZE,:] = batch_embeddings[0][:,:]
                position += MAX_BATCH_SIZE
                progress_bar.update(MAX_BATCH_SIZE)

        return embeddings
