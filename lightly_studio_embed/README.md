# LightlyStudio Embed

Serve your own embedding model to [LightlyStudio](https://github.com/lightly-ai/lightly-studio)
over HTTP, so that your model's weights never leave your machine.

The package deliberately depends on nothing but an HTTP server, so that it installs next to your
own CUDA and torch pins.

## Usage

Implement the capability classes your model supports, then serve it:

```python
from lightly_studio_embed import EmbeddingResult, ImageBytesEmbedder, TextEmbedder, serve


class MyEmbedder(TextEmbedder, ImageBytesEmbedder):
    @property
    def space_key(self) -> str:
        return "acme/clip@v3"

    @property
    def dimension(self) -> int:
        return 512

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        vectors = my_model.encode_text(texts)
        return EmbeddingResult(embeddings=vectors.tolist(), kept_indices=list(range(len(texts))))

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        ...


serve(MyEmbedder(), host="0.0.0.0", port=8080, api_key="the-key-you-paste-into-lightlystudio")
```

`serve` mounts `GET /v1/describe`, which reports the identity, capabilities and limits of the
server, plus one endpoint per capability the class implements — here `/v1/embed/texts` and
`/v1/embed/images/bytes`, and nothing else. An input the model cannot decode is left out of
`kept_indices` rather than failing the batch, and a method you have not finished yet raises
`CapabilityNotImplementedError`, which answers 501.

The bytes endpoints take a `multipart/form-data` body with one part per item, in the field
`files`. Every path and that field name are constants in `lightly_studio_embed.protocol`,
alongside the wire models, so an implementation in another language has one definition to
follow.

Nothing is published to PyPI yet. Once it is released, installing it will be:

```bash
pip install lightly-studio-embed
```
