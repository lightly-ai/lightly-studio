# Run LightlyStudio from a Notebook

You can run LightlyStudio in a Jupyter notebook or in Google Colab. With this setup, you can
load some data, start the GUI in the background, and run Python code while the GUI is still open.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_notebook.ipynb)


### Cell 1: Imports
```python
import lightly_studio as ls
from lightly_studio.dataset import env
from lightly_studio.utils import download_example_dataset
```

### Cell 2: Create a dataset from COCO data
```python
dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")
dataset = ls.ImageDataset.load_or_create()
dataset.add_samples_from_coco(
    annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
    images_path=f"{dataset_path}/coco_subset_128_images/images",
)
```

### Cell 3: Start the GUI in the background

Unlike `ls.start_gui()`, the command `ls.start_gui_background()` does not block the notebook,
so you can run Python code while the GUI is still open.

```python
env.LIGHTLY_STUDIO_HOST = "0.0.0.0"  # Colab needs 0.0.0.0 to expose the port.
ls.start_gui_background()
```

### Cell 4: Open the GUI

#### Browser with a Local Jupyter Notebook

If you are running a Jupyter notebook locally, click on the link printed in the output
to open the GUI in your browser.

#### IFrame in a Jupyter Notebook

```python
from IPython.display import IFrame, display

display(IFrame(env.APP_URL, width=1000, height=800))
```

#### IFrame in a Colab Notebook

```python
from google.colab import output

output.serve_kernel_port_as_iframe(env.LIGHTLY_STUDIO_PORT, width=1000, height=800)
```

### Cell 5: Stop the background GUI server

```python
ls.stop_gui_background()
```
