---
title: "Plugins: Extend LightlyStudio's Workflows"
description: Extend LightlyStudio with plugins for auto-labeling, SAM3 image segmentation, and video bounding box propagation, or build your own custom plugin.
---

# Plugins

LightlyStudio offers the possibility to extend its functionality by using plugins. Users can define their own plugins or use pre-defined ones.

LightlyStudio plugins can add workflows such as image segmentation with SAM3, auto-labeling for object detection, and video plugins for tasks like bounding box propagation across frames. This makes it possible to extend LightlyStudio with model-assisted annotation and dataset-specific automation directly inside the UI.

Plugins are shown in the UI based on their scope. The scope tells LightlyStudio which modality and context a plugin supports, for example dataset-level, image, or video frame context. The current view then determines which items the plugin runs on: in grid view, it uses the items matching the active filters; in detail view, it runs on the currently open item.

## How Plugins Are Registered

LightlyStudio registers a plugin in one of two ways:

| Mode | Use it for | What you do |
|---|---|---|
| Automatic discovery | Plugins installed as a Python package, such as the [LightlyStudio plugins](#lightlystudio-plugins) | Install the package. LightlyStudio registers it when the GUI starts. |
| Manual registration | Your own operator that is not packaged, for example a class in a local script | Call `operator_registry.register(...)` before `ls.start_gui()`. |

Do not register an installed plugin by hand. It then shows up twice in the GUI.

## LightlyStudio Plugins

Ready-to-use plugins are available in the [`lightly-studio-plugins`](https://github.com/lightly-ai/lightly-studio-plugins) repository. Each plugin lives in its own subdirectory under `plugins/` and can be installed directly from the repository.

### Available Plugins

- [BBox auto propagation nano tracker](https://github.com/lightly-ai/lightly-studio-plugins/tree/main/plugins/bbox_auto_propagation_nano_tracker/)  
  Propagates boxes from one annotated video frame to other frames in the same video.

    ??? note "Details"

        If triggered from a frame, all bounding box annotations on that frame are
        propagated. If triggered from an annotation, only the selected annotation is
        propagated.

        - Scope: video only, within a single video
        - Entry points: frame or annotation
        - Controls: forward and backward propagation windows in seconds
        - Tradeoff: uses OpenCV NanoTracker, which is lightweight and fast on many
          machines but less robust on difficult motion, occlusion, or scale changes
        - Maintainer: Lightly
        - Install:
          `pip install git+https://github.com/lightly-ai/lightly-studio-plugins.git#subdirectory=plugins/bbox_auto_propagation_nano_tracker/`

- [SAM3 Segmentation](https://github.com/lightly-ai/lightly-studio-plugins/tree/main/plugins/sam3_segmentation/)  
  Segments all instances matching a text prompt in a single image or across the current view.

    ??? note "Details"

        This is designed for dataset-wide prompt-based labeling workflows with
        class-like prompts such as `person`, `car`, or `dog`.

        - Scope: single image or images in the current view
        - Input: text prompt
        - Output: segmentation masks
        - Annotation class: the prompt text is used as the annotation class name
        - Requirement: Hugging Face access to `facebook/sam3`
        - Maintainer: Lightly
        - Install:
          `pip install git+https://github.com/lightly-ai/lightly-studio-plugins.git#subdirectory=plugins/sam3_segmentation/`

- [LightlyTrain object detection inference](https://github.com/lightly-ai/lightly-studio-plugins/tree/main/plugins/lightly_train_object_detection_inference/)  
  Runs LightlyTrain object detection inference on one image or the current view for auto-labeling.

    ??? note "Details"

        You can use built-in LightlyTrain models for quick bootstrapping or provide a
        path to your own LightlyTrain checkpoint.

        - Scope: single image or images in the current view
        - Input: LightlyTrain model name or local path to a LightlyTrain checkpoint
        - Output: object detection annotations
        - Annotation classes: annotation classes are read from the loaded model and created in the
          dataset if they do not exist yet
        - Recommended models:
          `dinov3/convnext-large-ltdetr-coco` for best performance,
          `dinov3/vits16-ltdetr-coco` for a speed/quality balance,
          `picodet-l-coco` for resource-constrained environments
        - Maintainer: Lightly
        - Install:
          `pip install git+https://github.com/lightly-ai/lightly-studio-plugins.git#subdirectory=plugins/lightly_train_object_detection_inference/`

**[Explore all available plugins on GitHub →](https://github.com/lightly-ai/lightly-studio-plugins)**

### Install LightlyStudio Plugins

Replace `<plugin_name>` with the folder name of the plugin you want to install:

```bash
pip install "git+https://github.com/lightly-ai/lightly-studio-plugins.git#subdirectory=plugins/<plugin_name>/"
```

Once installed, the plugin is registered automatically the next time you start the GUI.
You do not need to call `operator_registry.register`. If the GUI is already running,
restart it.

To remove a plugin, uninstall its package with `pip uninstall`,
using the package name defined in the plugin's `pyproject.toml` (typically matching the
plugin folder name).

### Example: LightlyStudio SAM3 Plugin

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/sam3_plugin.mp4" type="video/mp4">
</video>

The `sam3_segmentation` plugin brings interactive, model-assisted segmentation to
LightlyStudio using Segment Anything Model 3 (SAM3). Install it with:
```bash
pip install "git+https://github.com/lightly-ai/lightly-studio-plugins.git#subdirectory=plugins/sam3_segmentation/"
```
!!! info "Prerequisites"
    This plugin requires access to the SAM3 model on Hugging Face. Read the
    [sam3_segmentation README](https://github.com/lightly-ai/lightly-studio-plugins/tree/main/plugins/sam3_segmentation)
    before installing to make sure you have the necessary access and dependencies set up.

Once installed, the SAM3 segmentation plugin appears in the operator menu. Select an
image or a set of images, trigger the operator, and SAM3 will generate segmentation
masks directly inside LightlyStudio.

## Build Your Own Plugin

The LightlyStudio operator plugin makes it possible to call a python function in the backend through a dialog in the graphical user interface (GUI) alias frontend. After you register an operator, the GUI lists it automatically. While you develop an operator, register it manually in your script (see below). To share it, package it so LightlyStudio discovers it on install (see [Package Your Plugin](#package-your-plugin)). For operators using the builtin parameter types, the dialog in the GUI is generated and rendered automatically.

### Operator Plugin

An operator plugin is defined by the following attributes of the [`BaseOperator`](../api/plugin.md#lightly_studio.plugins.base_operator.BaseOperator) schema:

- name: The name of the operator that will also be used in the GUI.
- description: A detailed description of what the operator does.
- parameters: A list of inputs exposed in the GUI. Supported parameter types are documented under [`Parameter`](../api/plugin.md#parameter)
- supported_scopes: A list of [`OperatorScope`](../api/plugin.md#lightly_studio.plugins.operator_context.OperatorScope) values that determine where the operator should appear in the GUI. In most cases, you will use one of these:
  - `ROOT` for dataset-level operators
  - `IMAGE` for image collections
  - `VIDEO_FRAME` for video frame collections
- execute: The method that is used to execute the actual action. It will receive the parameters from the GUI.


#### Hello World 

![Hello World Plugin](https://storage.googleapis.com/lightly-public/studio/plugin_hello_world.gif){ width="100%" }

An example `Hello World" operator plugin looks like this:

```python title="greeting_operator.py"
from dataclasses import dataclass

from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_context import OperatorScope
from lightly_studio.plugins.parameter import StringParameter


@dataclass
class GreetingOperator(BaseOperator):
    name: str = "GreetingOperator"
    description: str = "This operator greet you"

    @property
    def parameters(self):
        return [
            StringParameter(
                name="name",
                required=True,
                default="beautiful and smart person",
                description="your name"
            ),
        ]
    
    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.ROOT]
    
    def execute(self, *, session, context, parameters):
        your_name = parameters.get("name", "")
        return OperatorResult(success=True, message=f"Hello {your_name}!")
```

To make an operator known to the application, you register it manually (see [How Plugins Are Registered](#how-plugins-are-registered)). For this you need to extend our main execution .py file:

```python title="example_operator.py"
import lightly_studio as ls
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.utils import download_example_dataset
from greeting_operator import GreetingOperator

dataset_path = download_example_dataset(download_dir="dataset_examples")

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=f"{dataset_path}/coco_subset_128_images/images")

# Register the operator to make it available to the application
operator_registry.register(GreetingOperator())

ls.start_gui()
```

After launching the GUI, the new plugin appears in the menu at the top-right corner.

#### LightlyStudio Auto-Labeling Plugin

![LightlyTrain plugin](https://storage.googleapis.com/lightly-public/studio/plugin_LightlyTrain_autoOD.gif){ width="100%" }

In this example we create an auto-labeling operator plugin powered by LightlyTrain, so make sure `lightly-train` is installed via `pip install lightly-train`. Compared to the Hello World example, this operator plugin introduces two inputs: the model name and the confidence threshold used for predictions. These parameters let you choose a pre-trained LightlyTrain model and control how confident detections must be before they are written back to LightlyStudio.

```python title="lightly_train_auto_label_od_operator.py"
from dataclasses import dataclass

import lightly_train
from PIL import Image
from lightly_train._commands.predict_task_helpers import prepare_coco_entries as prepare_entries

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_context import OperatorScope
from lightly_studio.plugins.parameter import FloatParameter, StringParameter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers import annotation_label_resolver, annotation_resolver, image_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


def _preload_label_map(session, dataset_id, class_names):
    """Pre-creates all necessary labels in the DB and returns a lookup map.

    Args:
        session: Database session.
        class_names: List of class names the model supports (e.g. ['car', 'person']).

    Returns:
        A dictionary mapping label names to their DB UUIDs.
    """
    label_map = {}

    for name in class_names:
        # Check if label exists in db
        label = annotation_label_resolver.get_by_label_name(session=session, dataset_id=dataset_id, label_name=name)

        # Create if missing
        if label is None:
            label_create = AnnotationLabelCreate(dataset_id=dataset_id, annotation_label_name=name)
            label = annotation_label_resolver.create(session=session, label=label_create)

        label_map[name] = label.annotation_label_id

    return label_map

@dataclass
class LightlyTrainAutoLabelingODOperator(BaseOperator):
    name: str = "LightlyTrain: OD auto-labeling"
    description: str = "This plugin allows to use pre-trained LightlyTrain models to perform auto-labeling for Object Detection."

    @property
    def parameters(self):
        return [
            StringParameter(
                name="Model",
                required=True,
                description="The name of the pre-trained model to be used.",
                default="dinov3/convnext-tiny-ltdetr-coco"
            ),
            FloatParameter(
                name="Threshold",
                default=0.4,
                description="The confidence threshold to be applied to the predictions."
            ),
        ]
    
    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.IMAGE]

    def execute(self, *, session, context, parameters):
        model_name = parameters["Model"]
        try:
            model = lightly_train.load_model(model_name)
        except ValueError as e:
            return OperatorResult(success=False, message=f"Model load failed: {str(e)}")
        
        if (parameters["Threshold"] > 1.0) or (parameters["Threshold"] < 0.0):
            return OperatorResult(success=False, message="Threshold must be in range 0.0 to 1.0")

        collection_name = f"lightly_train_auto_label__{model_name}"
        raw_classes = getattr(model, "classes", {})
        label_map = _preload_label_map(session, context.collection_id, list(raw_classes.values()))

        # Getting all samples for the provided context
        context_filter = None
        if context.context_filter:
            if isinstance(context.context_filter, SampleFilter):
                context_filter = ImageFilter(sample_filter=context.context_filter)
            elif isinstance(context.context_filter, ImageFilter):
                context_filter = context.context_filter

        samples = image_resolver.get_all_by_collection_id(
            session=session,
            collection_id=context.collection_id,
            filters=context_filter
        )

        # Running inference
        annotations_buffer = []
        for sample in samples.samples:
            image = Image.open(sample.file_path_abs).convert("RGB")

            preds = model.predict(image, threshold=parameters["Threshold"])
            entries = prepare_entries(predictions=preds, image_size=(sample.width, sample.height))

            for entry in entries:
                annotations_buffer.append(
                    AnnotationCreate(
                        parent_sample_id=sample.sample_id,
                        annotation_label_id=label_map[raw_classes[entry["category_id"]]],
                        annotation_type=AnnotationType.OBJECT_DETECTION,
                        x=int(entry["bbox"][0]),
                        y=int(entry["bbox"][1]),
                        width=int(entry["bbox"][2]),
                        height=int(entry["bbox"][3]),
                        confidence=entry["score"],
                    )
                )

        annotation_resolver.create_many(
            session=session,
            parent_collection_id=context.collection_id,
            annotations=annotations_buffer,
            collection_name=collection_name,
        )
        total_created = len(annotations_buffer)

        return OperatorResult(
            success=True, message=f"Auto-labeling complete. Added {total_created} annotations."
        )

```

```python title="example_operator_auto_label.py"
import lightly_studio as ls
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.utils import download_example_dataset
from lightly_train_auto_label_od_operator import LightlyTrainAutoLabelingODOperator

dataset_path = download_example_dataset(download_dir="dataset_examples")

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=f"{dataset_path}/coco_subset_128_images/images")

# Register the operator to make it available to the application
operator_registry.register(LightlyTrainAutoLabelingODOperator())

ls.start_gui()
```

### Package Your Plugin

To make LightlyStudio discover your operator on install, declare an entry point in the
`lightly_studio.plugins` group of your package's `pyproject.toml`. The entry point
references a `BaseOperator` subclass. LightlyStudio creates the operator with no
arguments, so all fields need default values.

```toml title="pyproject.toml"
[project.entry-points."lightly_studio.plugins"]
greeting = "my_plugin.greeting_operator:GreetingOperator"
```

After `pip install .`, remove the `operator_registry.register` call from your script.
For complete examples, see the
[lightly-studio-plugins](https://github.com/lightly-ai/lightly-studio-plugins) repository.
