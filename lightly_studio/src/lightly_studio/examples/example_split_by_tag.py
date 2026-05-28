"""Demo: split a dataset into a new one from a tag via a GUI-triggered plugin.

How to use:
    1. Run this script.
    2. In the GUI, tag a few samples (e.g. with a tag named "keep").
    3. Open the operators menu and run "Split dataset by tag" with
       tag="keep" and new_dataset_name="my_subset".
    4. The sidebar will list a new dataset containing only the tagged samples.
"""

from __future__ import annotations

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.examples.split_by_tag_operator import SplitByTagOperator
from lightly_studio.plugins.operator_registry import operator_registry

env = Env()
env.read_env()

db_manager.connect(cleanup_existing=True)

dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=dataset_path)

operator_registry.register(operator=SplitByTagOperator())

ls.start_gui()
