# Label with Your Own Model

!!! example "Beta"
    Labeling models are in beta. The interface may change in future releases without a
    deprecation period.

You can label images in the GUI with a model of your own, for example a detector that you
trained with [LightlyTrain](https://docs.lightly.ai/train). The model suggests annotations for the
open image. You delete the wrong ones and save the rest. Nothing is saved before you confirm.

Labeling models support object detection and instance segmentation on images.

## Connect a model

Subclass `ls.LabelingModel` and register an instance before you start the GUI:

```python
import lightly_studio as ls
from PIL.Image import Image


class MyModel(ls.LabelingModel):
    model_id = "my-detector"
    task = ls.ModelTask.OBJECT_DETECTION
    class_names = ["car", "person"]

    def predict(self, image: Image, threshold: float) -> list[ls.PredictedAnnotation]:
        # Run your model here.
        return [
            ls.PredictedAnnotation(class_name="car", box=(10, 20, 110, 80), score=0.9),
        ]


ls.register_labeling_model(model=MyModel())

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path="path/to/images")
ls.start_gui()
```

- `model_id` is the name that the GUI shows.
- `task` is `ls.ModelTask.OBJECT_DETECTION` or `ls.ModelTask.INSTANCE_SEGMENTATION`.
- `class_names` lists the annotation classes that the model can predict.
- `predict` gets the image as an RGB PIL image, and the confidence threshold that the user
  selected. It returns one `ls.PredictedAnnotation` for each object.

A `PredictedAnnotation` holds the annotation class, a box `(x_min, y_min, x_max, y_max)` in
pixels, and a score from 0 to 1. An instance segmentation model also sets `mask`, a boolean array
with the height and the width of the image.

The registration is not saved in the dataset. Register the model in each process that starts the
GUI. The GUI calls `predict` from several threads, so hold a lock in `predict` if your model is
not thread-safe.

See `examples/example_labeling_model.py` for a runnable example with a LightlyTrain model.

## Run the model on a remote server

Use a remote server when the model must not run in the process of LightlyStudio. For example,
the model needs its own GPU or its own dependency versions.

**1. Serve the model.** Install `lightly-studio-serve` on the server and serve the same
`LabelingModel` class:

```python
from lightly_studio_serve import serve

serve(labeling_model=MyModel(), port=8080, api_key="your-secret-key")
```

`serve` binds `127.0.0.1:8080` by default. Use TLS for any other address, because each
request carries the API key; `serve` and LightlyStudio warn about plain HTTP. See the
[`lightly_studio_serve` README](https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio_serve/README.md)
for TLS and limits.

**2. Connect the dataset.** Register the server once for the dataset:

```python
ls.register_remote_labeling_model(
    dataset=dataset, url="http://gpu-box:8080", api_key="your-secret-key"
)
```

The dataset stores the URL and the API key, so a later process shows the model in the GUI with
no registration. Call the function again to change the URL or the key.

!!! warning "The API key is stored in plain text"
    The dataset stores the API key in plain text. Everyone who can read the database can read
    the key.

If a model that `register_labeling_model` registered has the same `model_id` as a saved server,
the registered model is used. A server that cannot be reached is not shown in the GUI.
LightlyStudio tries it again after 30 seconds.

See `examples/example_remote_labeling_model.py` for a runnable example.

## Label an image

1. Open an image and click `Edit annotations`.
2. Select the `Label with model` tool in the toolbar. The tool shows only if a model is
   registered.
3. Select a model and a confidence threshold, then click `Run model`.
4. Delete the suggested annotations that are wrong.
5. Click `Save`. The annotations are added to the image. An annotation class that does not
   exist yet is created.

For an instance segmentation model, you can save the suggested annotations as masks or as boxes.

!!! note "Label many images at once"
    The tool labels one image at a time, with a review step. To add the predictions of a model
    to many images without a review, use the [Python API](annotations.md) or an
    [operator plugin](../ecosystem/plugins.md).
