# LightlyStudio Embed

Serve your own embedding model to [LightlyStudio](https://github.com/lightly-ai/lightly-studio)
over HTTP, so that your model's weights never leave your machine.

The package depends on an HTTP server, numpy and Pillow. It does not depend on torch, CUDA or
LightlyStudio. You can therefore install it next to your own pins.

`lightly_studio_embed.embedder` holds the base classes for a model. `lightly_studio_embed.types`
holds the values that these classes receive and return. LightlyStudio uses the same classes for
its own embedders.

## Usage

Implement the capability classes your model supports, then serve it:

```python
from lightly_studio_embed import (
    EmbeddingResult,
    EmbeddingSpaceSpec,
    ImageBytesEmbedder,
    TextEmbedder,
    serve,
)


class MyEmbedder(TextEmbedder, ImageBytesEmbedder):
    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="acme/clip@v3", dimension=512)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        vectors = my_model.encode_text(texts)
        return EmbeddingResult(embeddings=vectors, kept_indices=list(range(len(texts))))

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        ...


serve(
    MyEmbedder(),
    host="0.0.0.0",
    port=8080,
    api_key="the-key-you-paste-into-lightlystudio",
    ssl_certfile="cert.pem",
    ssl_keyfile="key.pem",
)
```

The bearer token travels in the request, so plain HTTP shows it to the network. Give
`ssl_certfile` and `ssl_keyfile` for any address that is not loopback. You can also end TLS at a
proxy. In that case the hop from the proxy to this server must use HTTPS or mTLS, or it must stay
on loopback or on a private network that you trust. TLS at the proxy alone does not protect the
token on that hop. `serve` gives a warning when it has no certificate of its own.

`EmbeddingResult.embeddings` is a float32 numpy array with the shape
`(len(kept_indices), dimension)`. LightlyStudio uses the same class for its own embedders.

`serve` mounts `GET /v1/describe`, which reports the identity, the capabilities and the limits of
the server. It also mounts one endpoint for each capability that the class implements. The
example above gets `/v1/embed/texts` and `/v1/embed/images/bytes`, and no other endpoint. The
server omits an input that the model cannot decode from `kept_indices`. It does not fail the
batch. Subclass only the interfaces whose methods you have written: the class list is the
advertisement, so there is no way to advertise a capability and then not serve it.

The bytes endpoints take a `multipart/form-data` body. The body holds one part for each item, in
the field `files`. Every path and that field name are constants in `lightly_studio_embed.protocol`,
next to the wire models. An implementation in another language therefore has one definition to
follow.

Nothing is published to PyPI yet. Once it is released, installing it will be:

```bash
pip install lightly-studio-embed
```
