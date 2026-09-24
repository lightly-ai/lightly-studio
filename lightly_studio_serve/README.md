# LightlyStudio Serve

Serve your own embedding model to [LightlyStudio](https://github.com/lightly-ai/lightly-studio)
over HTTP, so that your model's weights never leave your machine.

The package depends on an HTTP server, numpy and Pillow. It does not depend on torch, CUDA or
LightlyStudio. You can therefore install it next to your own pins.

`lightly_studio_serve.embedder` holds the base classes for a model. `lightly_studio_serve.types`
holds the values that these classes receive and return. LightlyStudio uses the same classes for
its own embedders.

## Usage

Implement the capability classes your model supports, then serve it:

```python
from lightly_studio_serve import (
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


serve(MyEmbedder(), api_key="the-key-you-paste-into-lightlystudio")
```

`serve` binds `127.0.0.1:8080` by default, where the requests stay on the machine. TLS is
optional there and off unless you ask for it.

The bearer token travels in the request, so plain HTTP shows it to the network. Any address that
is not loopback therefore needs TLS. Give `ssl_certfile`, and `ssl_keyfile` if the certificate
file does not already hold the key, to end TLS in the server itself:

```python
serve(
    MyEmbedder(),
    host="0.0.0.0",
    port=8080,
    api_key="the-key-you-paste-into-lightlystudio",
    ssl_certfile="cert.pem",
    ssl_keyfile="key.pem",
)
```

You can also end TLS at a proxy and keep these two arguments out. In that case the hop from the
proxy to this server must use HTTPS or mTLS, or it must stay on loopback or on a private network
that you trust. TLS at the proxy alone does not protect the token on that hop. `serve` gives a
warning when it binds an address that is not loopback and has no certificate of its own.

`EmbeddingResult.embeddings` is a float32 numpy array with the shape
`(len(kept_indices), dimension)`. LightlyStudio uses the same class for its own embedders.

`serve` mounts `GET /v1/describe`, which reports the identity, the capabilities and the limits of
the server. It also mounts one endpoint for each capability that the class implements. The
example above gets `/v1/embed/texts` and `/v1/embed/images/bytes`, and no other endpoint. The
server omits an input that the model cannot decode from `kept_indices`. It does not fail the
batch. Subclass only the interfaces whose methods you have written: the class list is the
advertisement, so there is no way to advertise a capability and then not serve it.

The bytes endpoints take a `multipart/form-data` body. The body holds one part for each item, in
the field `files`. Every path and that field name are constants in `lightly_studio_serve.protocol`,
next to the wire models. An implementation in another language therefore has one definition to
follow.

Nothing is published to PyPI yet. Once it is released, installing it will be:

```bash
pip install lightly-studio-serve
```

## Check your implementation

The protocol is the contract, so a server in any language can serve LightlyStudio. Point
the conformance kit at one to see whether it does:

```bash
lightly-studio-serve conformance http://127.0.0.1:8080
```

The run reads `/v1/describe`, then sends one fixed probe for each capability the server
advertises, and checks every answer against `/v1/describe` and the protocol rules. It needs
no dataset, so you can run it before LightlyStudio ever sees the server.

The report names one outcome per capability, so a model that reads images and no video
reads as `video_bytes  not advertised` rather than as a failure:

```text
http://127.0.0.1:8080

protocol 1.0
space    acme/clip@v3
vectors  512 values
ready    yes

text         passed
image_bytes  passed
video_bytes  not advertised

PASSED
```

The process ends with 0 when the server passes, so you can run the kit in your own build.
Pass `--api-key`, or set `LIGHTLY_STUDIO_SERVE_API_KEY`, for a server that expects a token.

## Connect the server to LightlyStudio

LightlyStudio embeds search queries on the server once you point a dataset at it. The
dataset must already hold embeddings in the space that the server produces:

```python
import lightly_studio as ls

ls.register_remote_embedder(
    dataset=dataset, url="http://127.0.0.1:8080", api_key="the-key-you-paste-into-lightlystudio"
)
```

See the
[LightlyStudio embeddings guide](https://docs.lightly.ai/studio/core_concepts/embeddings/#serving-an-embedder-from-a-remote-server)
for the full flow and its limits, and
[`example_remote_embedder.py`](https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_remote_embedder.py)
for a runnable example.
