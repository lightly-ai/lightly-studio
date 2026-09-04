# LightlyEmbed

Serve your own embedding model to [LightlyStudio](https://github.com/lightly-ai/lightly_studio)
over HTTP, so that your model's weights never leave your machine.

The package deliberately depends on nothing but an HTTP server, so that it installs next to your
own CUDA and torch pins.

There is no public API yet, and nothing is published to PyPI: this only reserves the package. Once
it is released, installing it will be:

```bash
pip install lightly-embed
```
