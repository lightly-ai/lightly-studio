"""Row-uniformity image metric.

Computes the fraction of "uniform" rows in an image. A higher score means the image is
more likely to be blank / corrupt / a transition frame (e.g. a fade to black), so a low
score indicates a content-rich frame.

This is a port of the ``uniformRowRatio`` metric used in LightlyOne
(``lightly_worker/inspect_rgb/rgb_properties/row_uniformity.py``), kept close to the
original so behavior matches what existing users are used to.
"""

from __future__ import annotations

import torch
from PIL.Image import Image as PILImage
from torch import Tensor
from torch.backends import mkldnn
from torch.nn import functional as nn_functional
from torchvision.transforms import functional as tr_functional

RESIZE_MAX_HEIGHT = 400
UNIFORM_PIXEL_LAPLACE_THRESHOLD = 5 / 255
UNIFORM_ROW_PIXEL_RATIO = 0.97

# Laplacian filter kernel used to detect uniform (near-constant) pixel neighborhoods.
LAPLACIAN_KERNEL = torch.tensor(
    [[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]], dtype=torch.float32
).view(1, 1, 3, 3)


def compute_uniform_row_ratio(image_greyscale: PILImage) -> float:
    """Compute the row-uniformity score of a greyscale image.

    The result is a float in ``[0, 1]``. Higher means the image is more likely to be
    blank / corrupt: it is the proportion of rows in which almost all pixels are uniform.

    Returns ``0.0`` if the image has a dimension smaller than 3 pixels (the Laplacian
    filter cannot be applied in that case).

    Algorithm:
    1. Resize to a max height of ``RESIZE_MAX_HEIGHT`` pixels.
    2. Apply the Laplacian filter.
    3. Detect uniform pixels (filter response below a threshold).
    4. Compute the ratio of uniform pixels per row.
    5. Return the proportion of rows whose ratio exceeds ``UNIFORM_ROW_PIXEL_RATIO``.

    Args:
        image_greyscale: A single-channel (greyscale) PIL image.
    """
    orig_width, orig_height = image_greyscale.size
    if orig_width < 3 or orig_height < 3:
        return 0.0

    tensor_image = tr_functional.to_tensor(pic=image_greyscale)

    # Resize to a max height of RESIZE_MAX_HEIGHT pixels.
    shrink_factor = RESIZE_MAX_HEIGHT / orig_height
    if shrink_factor < 1:
        target_height = int(orig_height * shrink_factor)
        # The target width must stay at least 3, otherwise the Laplacian filter fails.
        target_width = max(3, int(orig_width * shrink_factor))
        tensor_image = tr_functional.resize(
            img=tensor_image,
            size=(target_height, target_width),
            antialias=False,
        )

    uniform_pixels = _detect_uniform_pixels(tensor_image=tensor_image)

    # Detect uniform rows from the ratio of uniform pixels per row.
    row_ratios = uniform_pixels.mean(dim=2)
    uniform_rows = (row_ratios > UNIFORM_ROW_PIXEL_RATIO).float()

    return torch.mean(uniform_rows).item()


def _detect_uniform_pixels(tensor_image: Tensor) -> Tensor:
    """Detect uniform pixels via a Laplacian filter.

    Returns a float tensor that is 1 where the filter response is near zero (uniform pixel)
    and 0 otherwise.
    """
    # Disable the MKL-DNN backend: it switches conv2d algorithms based on image size, which
    # can cause large memory spikes when processing many differently sized frames.
    with mkldnn.flags(enabled=False):
        tensor_image = nn_functional.conv2d(
            input=tensor_image.unsqueeze(0), weight=LAPLACIAN_KERNEL
        ).squeeze(0)

    return (
        (tensor_image > -UNIFORM_PIXEL_LAPLACE_THRESHOLD)
        & (tensor_image < UNIFORM_PIXEL_LAPLACE_THRESHOLD)
    ).float()
