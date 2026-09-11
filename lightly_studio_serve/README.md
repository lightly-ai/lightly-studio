# LightlyStudio Serve

Serve your own embedding model to [LightlyStudio](https://github.com/lightly-ai/lightly-studio)
over HTTP, so that your model's weights never leave your machine.

**The HTTP server is not implemented yet.** So far the package holds the base classes and the
types that LightlyStudio and a server will share.

The package depends on an HTTP server, numpy and Pillow. It does not depend on torch, CUDA or
LightlyStudio. You can therefore install it next to your own pins.

`lightly_studio_serve.embedder` holds the base classes for a model. `lightly_studio_serve.types`
holds the values that these classes receive and return. LightlyStudio uses the same classes for
its own embedders.

Nothing is published to PyPI yet. Once it is released, installing it will be:

```bash
pip install lightly-studio-serve
```
