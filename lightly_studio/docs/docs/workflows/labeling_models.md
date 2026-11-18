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
