# LightlyStudio Embed

Serve your own embedding model to [LightlyStudio](https://github.com/lightly-ai/lightly-studio)
over HTTP, so that your model's weights never leave your machine.

The package depends on an HTTP server and numpy, and deliberately nothing else — no torch, no
CUDA, no LightlyStudio — so that it installs next to your own pins. Numpy is there because
`EmbeddingResult` is shared with `lightly-studio`, whose ingest paths index the array.

The wire models of the protocol and the embedder base classes live in
`lightly_studio_embed.protocol` and `lightly_studio_embed.embedder`. There is no server yet, and
nothing is published to PyPI. Once it is released, installing it will be:

```bash
pip install lightly-studio-embed
```
