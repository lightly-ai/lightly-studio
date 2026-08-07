# Custom Embedding Models

LightlyStudio computes embeddings for your samples during indexing and uses them for text
search, image search, similarity, and sampling. If you index with your own embedding model,
those embeddings live in the database and everything that only *reads* them keeps working.

Search is different. Typing a query embeds that query, which needs a live copy of your model.
On a hosted LightlyStudio instance your model is not present, so LightlyStudio needs somewhere
to send query text and query images.

The answer is an **embedding service**: a small HTTP endpoint you run on your own network that
serves the same model you indexed with. The browser calls it directly.

```
                    ┌──────────────────────┐
   your browser ───►│ hosted LightlyStudio │  filters, ranking, stored vectors
        │           └──────────────────────┘
        │  query text / query image
        ▼
  ┌───────────────────────┐
  │ your embedding service│  your network, your weights
  └───────────────────────┘
```

Your model and your queries never reach Lightly's infrastructure, and Lightly's servers never
connect to your network. The browser hands the resulting vector to LightlyStudio, which uses it
to rank the stored embeddings.

## Registering a service

Pass `serving_url` when you register your model. The URL is stored next to the record of which
model produced the embeddings, so the two cannot drift apart:

```python
import lightly_studio as ls

ls.set_default_embedding_model(
    MyEmbeddingGenerator(),
    serving_url="https://gpu-box.corp.example:8123",
)

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path="/data/images")
```

To change the URL later without re-indexing, `PUT` the new one. This is keyed on the model, so
one call covers every collection indexed with it:

```bash
curl -X PUT https://studio.corp.example/api/embedding_models/my-model-v1/serving_url \
  -H 'Content-Type: application/json' \
  -d '{"serving_url": "https://new-gpu-box.corp.example:8123"}'
```

Send `{"serving_url": null}` to stop serving the model.

## The wire contract

Your service must answer three requests. A complete, runnable implementation is in
`lightly_studio/examples/example_embedding_service.py` — copy it and replace the model.

### `GET /info`

Called once when a collection is opened, so LightlyStudio knows what your model can do before
it draws the search bar.

```json
{
  "contract_version": "1",
  "model_id": "my-model-v1",
  "embedding_dimension": 512,
  "supports_text": true,
  "supports_image": true,
  "normalized": false
}
```

| Field | Meaning |
|---|---|
| `contract_version` | Always `"1"` today. |
| `model_id` | Must equal the `embedding_model_hash` your indexing code declares. See [Model identity](#model-identity). |
| `embedding_dimension` | Length of the vectors you return. |
| `supports_text` | `false` for a model with no text tower. Hides the text search box instead of offering one that always fails. |
| `supports_image` | `false` for a model that cannot embed images. |
| `normalized` | Whether your vectors are unit length. |

A missing `supports_*` flag is read as `false`.

### `POST /embed/text`

```
Content-Type: application/json

{"text": "a red car at night"}
```

Returns the vector as a JSON array: `[0.013, -0.221, ...]`.

### `POST /embed/image`

A `multipart/form-data` body with the image in a field named `image`. Returns a vector in the
same format.

Your service owns all preprocessing — resizing, cropping, normalization. LightlyStudio sends the
raw file exactly as the user supplied it.

## Model identity

`model_id` is a string **you** declare, not a digest of your weights. The rule is:

> Change `model_id` whenever your model starts producing different vectors.

LightlyStudio compares the `model_id` your service reports against the identifier recorded when
the collection was indexed. If they differ, search is disabled with an explicit message. It never
falls back to the built-in model: a built-in query vector compared against your embeddings
produces a confidently ordered list of unrelated results, with no error — and because 512 is a
common width, a dimension check would not catch it either.

The flip side is that this is trust-based. If you retrain and forget to bump `model_id`, search
returns quietly wrong results. The most reliable pattern is to have one source of truth — fetch
the id from the service itself when you index:

```python
import httpx

SERVING_URL = "https://gpu-box.corp.example:8123"
model_id = httpx.get(f"{SERVING_URL}/info").json()["model_id"]
```

## Requirements

**One model per process.** The URL is keyed on model identity, so three models means three
processes on three ports.

**HTTPS.** Hosted LightlyStudio is served over HTTPS, and browsers block plain-`http` requests
from an HTTPS page as mixed content. Your service needs a TLS certificate the browser trusts.
`http://` is accepted only for `localhost`, which browsers treat as a secure context.
LightlyStudio rejects a non-loopback `http://` URL when you save it, rather than letting it fail
later during a search.

**CORS.** The browser sends a cross-origin request, so your service must return
`Access-Control-Allow-Origin` for your LightlyStudio origin and answer the `OPTIONS` preflight.

**Private Network Access.** If your service is on a private address (`10.x`, `192.168.x`,
`172.16–31.x`) and LightlyStudio is on a public origin, Chrome sends a preflight carrying
`Access-Control-Request-Private-Network: true` and requires
`Access-Control-Allow-Private-Network: true` in the response. The example service does this.

**Reachable from each user's machine.** The browser makes the call, not the LightlyStudio
backend. A user on a VPN that does not route to the service will see search fail while a
colleague on the LAN sees it work.

Search is submit-triggered, so your service sees roughly one request per deliberate search.

## Security

**No authentication in v1.** An open port inside your own network is your security policy to
set. The contract reserves an `Authorization` header for a future token so adding one will not
require a protocol change.

**CORS is not authentication.** It stops other *websites* from reading your service's responses
in a browser. It does not stop `curl` from anything already on the network.

**Model extraction is not preventable.** Anyone who can run searches can collect
query/vector pairs. No scheme at this layer changes that.

**The serving URL is a sensitive setting.** Whoever writes it redirects every user's queries and
uploaded images to a host of their choosing — and because Lightly's servers are not in the path,
there is no trace of it on them. Restricting the update endpoint to administrators is not
implemented yet; treat write access to it as equivalent to intercepting search traffic.

## Troubleshooting

**"Could not reach the embedding service"** — Open the service URL directly in the same browser.
If that works but search does not, it is CORS or Private Network Access. Check the browser
console for the blocked preflight and confirm your service returns both
`Access-Control-Allow-Origin` and, for a private address,
`Access-Control-Allow-Private-Network`.

To reproduce a private-network block deliberately: serve the example service on a LAN address
over HTTPS, open a hosted LightlyStudio instance, and watch the Network tab for the `OPTIONS`
request to `/info`. A preflight that fails with a private-network error means the header is
missing or the browser policy has tightened further.

**"the service serves model X, but this collection was indexed with Y"** — The running service
is not the model that produced the stored embeddings. Either point the URL at the right service,
or re-index.

**Search works for you but not a colleague** — Their machine cannot reach the service. This is a
network path problem, not a LightlyStudio one.

## Limitations

- **Browser required.** There is no headless path; the Python API cannot run a text search
  against a custom model.
- **Video collections are not supported.** Video embeddings are hard-wired to the built-in
  model.
- **Your downtime looks like ours.** If the service is down, search is unavailable in
  LightlyStudio.
