# Use external embedding models in LightlyStudio

By default, LightlyStudio computes embeddings with built-in models on your machine. You
can replace them with an external embedding model, for example a model behind a hosted
API such as OpenRouter, OpenAI, Google Vertex AI, Voyage AI or Cohere.

In this tutorial, you learn the pattern that connects an external embedding model to
LightlyStudio. As an example, you use
[Gemini Embedding 2](https://openrouter.ai/google/gemini-embedding-2) through
[OpenRouter](https://openrouter.ai).

You will:

- Learn which features each type of embedding model enables in LightlyStudio.
- Write an embedder that sends images and text to a hosted embedding API.
- Register it, so that LightlyStudio uses it at ingestion and in the GUI.
- Ingest raw images and explore them with the embedding plot, text search and image search.
- Change to a different model or a different provider.

!!! example "Beta API"
    The embeddings API is in beta. Its interface may change in future releases
    without a deprecation period.

## Why use an external embedding model

The built-in models are small, so they run fast on a laptop. An external model is useful
when:

- You want a larger model, but you do not have a GPU.
- Your team already uses an embedding model in other systems, and you want the same
  vectors in LightlyStudio.
- You want to compare models from different providers on your data.

!!! warning "Your data leaves your machine"
    With a hosted API, the embedder sends each image and each text query to the provider.
    Do not use a hosted model for data that must stay on your machine. Read the data
    policy of the provider first. To keep the data on your own hardware, run the model on
    your own server. See
    [Serving an embedder from a remote server](../workflows/embeddings.md#serving-an-embedder-from-a-remote-server).

## How LightlyStudio uses an embedding model

LightlyStudio talks to each embedding model through an **embedder**: a Python class that
you write. The embedder subclasses one interface for each input that the model can embed.
Each interface enables one or more features:

| Interface | Method | Enables |
|---|---|---|
| `ImagePathEmbedder` | `embed_images` | Image embeddings at ingestion: embedding plot, similarity, sampling |
| `ImageCropPathEmbedder` | `embed_image_crops` | Annotation embeddings at ingestion |
| `ImageBytesEmbedder` | `embed_image_bytes` | Image search in the GUI |
| `TextEmbedder` | `embed_text` | Text search and text axes in the GUI |

Each embed method receives a list of inputs and returns an `ls.EmbeddingResult`:

- `embeddings`: a `float32` matrix with one row for each embedded input.
- `kept_indices`: the positions of the embedded inputs in the input list. If the embedder
  cannot read an input, it leaves out its position.

The embedder also gives `embedding_space_spec()`: a name (`space_key`) and the length
(`dimension`) of its vectors. LightlyStudio stores the name with the embeddings, and
compares only vectors with the same name.

The model type decides which interfaces you can subclass:

| Model type | Example | Interfaces | Features |
|---|---|---|---|
| Multimodal (text and images in one space) | Gemini Embedding 2, CLIP | All four | All |
| Image only | DINOv2 | The three image interfaces | All, except text search and text axes |
| Text only | `text-embedding-3-small` | `TextEmbedder` only | Not useful for images |

!!! note "Text search needs one shared space"
    Text search compares a text vector with image vectors. This works only if the model
    puts text and images in the same embedding space. Two separate models, one for text
    and one for images, do not give useful results.

## The example: OpenRouter and Gemini Embedding 2

OpenRouter gives one HTTP API for embedding models from many providers. You change the
model with one string, and you need only one API key. Gemini Embedding 2 is multimodal,
so the embedder can subclass all four interfaces.

The full code is in
[`example_openrouter_embedder.py`](https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_openrouter_embedder.py).
Download it to your working directory. The next steps explain its important parts.

## Step 1: Get an API key

1. Create an account on [openrouter.ai](https://openrouter.ai) and add credits.
2. Create a key on the [API keys page](https://openrouter.ai/settings/keys).
3. Set the key as an environment variable:

    ```bash
    export OPENROUTER_API_KEY="sk-or-..."
    ```

Install LightlyStudio. It works with **Python 3.9 to 3.14**.

```bash
pip install lightly-studio
```

The embedder uses `httpx`, which LightlyStudio installs. You do not need an
OpenRouter or Google SDK.

## Step 2: Write the embedder

The embedder subclasses the four interfaces:

```python
class OpenRouterEmbedder(
    ImagePathEmbedder,
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    TextEmbedder,
):
    ...
```

### The embedding space

The space key contains the provider, the model and the dimension:

```python
def embedding_space_spec(self) -> ls.EmbeddingSpaceSpec:
    return ls.EmbeddingSpaceSpec(
        space_key=f"openrouter/{self._model}@{self._dimension}",
        dimension=self._dimension,
    )
```

If you change the model or the dimension, LightlyStudio puts the new vectors in a new
space, and does not mix them with the old vectors.

Gemini Embedding 2 makes vectors with 3072 values. The example asks for 768 values with
the `dimensions` request field. Shorter vectors use less disk space and memory.

### One request

All inputs go to one endpoint, `POST https://openrouter.ai/api/v1/embeddings`. A text
input is a string. An image input is an object with a base64 JPEG data URL:

```python
payload = {
    "model": "google/gemini-embedding-2",
    "dimensions": 768,
    "input": [
        "a person on a bicycle",
        {
            "content": [
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
            ]
        },
    ],
}
```

The response has one item for each input. Each item has an `index` and an `embedding`.
The embedder sorts the items by `index` and makes a `float32` matrix:

```python
data = sorted(body["data"], key=lambda item: item["index"])
embeddings = np.asarray([item["embedding"] for item in data], dtype=np.float32)
```

### Images

Before the embedder sends an image, it makes the image smaller (1024 pixels on the long
side, by default) and encodes it as JPEG. This makes the requests smaller and faster.

```python
def _to_image_input(image: Image.Image, max_side: int) -> dict[str, Any]:
    image.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
        ]
    }
```

The image methods all use this function. They differ only in how they get the image:
`embed_images` reads a file, `embed_image_crops` reads a file and cuts out the box, and
`embed_image_bytes` decodes the uploaded bytes. If the embedder cannot read an image, it
skips the image and leaves out its position from `kept_indices`.

### Batches and retries

LightlyStudio gives the embedder up to 1024 images in one call. The embedder sends them
in batches of 16 inputs. A hosted API can fail for a short time, for example with HTTP 429
(rate limit) or HTTP 503. The embedder tries the request again after a wait, so that one
failure does not stop the ingestion. Errors that a new try cannot fix, such as HTTP 401
(bad key), stop the ingestion at once.

## Step 3: Ingest images

This tutorial uses the 128 images of the LightlyStudio example dataset. Download them:

```python
import lightly_studio as ls

ls.utils.download_example_dataset(download_dir="dataset_examples")
```

Set the path to the images:

```bash
export EXAMPLES_DATASET_PATH="dataset_examples/coco_subset_128_images/images"
```

The end of `example_openrouter_embedder.py` registers the embedder, ingests the images and
starts the GUI:

```python
ls.register_default_embedder(embedder=OpenRouterEmbedder(api_key=env.str("OPENROUTER_API_KEY")))

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=str(env.path("EXAMPLES_DATASET_PATH")))

ls.start_gui()
```

Register the embedder **before** you create the dataset. Then ingestion uses it in
place of the built-in model. Run the script:

```bash
python example_openrouter_embedder.py
```

The progress bar shows "Embedding with OpenRouter". The 128 images go in 8 requests and
take about 10 seconds. After it finishes, open the URL that the script prints.

!!! note "Start the GUI with the same embedder"
    The GUI embeds each text query and each uploaded image with the embedder of the
    dataset. If you start the GUI in a new Python process, call
    `ls.register_default_embedder(...)` with the same model and dimension before
    `ls.start_gui()`. Else text search and image search are not available.

## Step 4: Explore the dataset

- **Embedding plot.** Open the embedding plot. Images with similar content are near each
  other. Use the lasso to select a group, and look at its images in the grid.
- **Text search.** Type a query in the search field, for example "a pizza on a table".
  The query goes to the external model, and the grid shows the most similar images
  first. Each image shows its similarity to the query.
- **Image search.** Upload an image in the search field. The grid shows the images that
  are most similar to it.

## Step 5: Use a different model or provider

### Another model on OpenRouter

The embedder works with each OpenRouter model that embeds both images and text. Give the
model ID and a dimension that the model supports:

```python
embedder = OpenRouterEmbedder(
    api_key=env.str("OPENROUTER_API_KEY"),
    model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
    dimension=2048,
)
```

The [list of embedding models](https://openrouter.ai/api/v1/embeddings/models) shows the
input types of each model in `architecture.input_modalities`. If the model returns
vectors of a different length than `dimension`, the embedder raises an error that shows
the received shape. Set `dimension` to that length.

!!! note "Free models"
    Models with the `:free` suffix have low rate limits, and some requests take a long
    time. The embedder tries a request again after a timeout, but a large ingestion can
    still be slow. Use a paid model for large datasets.

### Another provider

To use a different hosted API, copy the example and change only the parts that are
specific to the provider:

| Part | What to change |
|---|---|
| `__init__` | The base URL and the authentication header of the provider. |
| `embedding_space_spec` | The prefix of the space key, for example `"vertex/..."`. |
| `_request_embeddings` | The request body and how to read the vectors from the response. |
| `_to_image_input` | How the provider accepts an image, for example base64 or a URL. |
| Base classes | Subclass only the interfaces for the inputs that the model can embed. |

The batching, the retries, the image reading and `kept_indices` stay the same.

## Cost and limits

- **Cost.** Hosted APIs charge for each input. With Gemini Embedding 2 on OpenRouter,
  one image is 258 tokens, which is about $0.00012. The 128 images of this tutorial cost
  about $0.015, and 100,000 images cost about $12. A text query costs almost nothing.
  Prices can change, so check the
  [model page](https://openrouter.ai/google/gemini-embedding-2). OpenRouter shows your
  total cost on the [activity page](https://openrouter.ai/activity).
- **Re-ingestion.** Each ingestion sends all new images to the API again. Keep the
  database and use `ls.ImageDataset.load_or_create` to add only new images.
- **Speed.** One request with 16 images takes about one second. Thus 100,000 images take
  about two hours. For more speed, send more batches at the same time from more than one
  thread.
- **Rate limits.** Each provider limits the number of requests. The embedder waits and
  tries again when it receives HTTP 429.

## Conclusion

You connected an external embedding model to LightlyStudio with one Python class. The
pattern is the same for each model: subclass the interfaces for the inputs that the model
can embed, convert the inputs to the request format of the provider, and return the
vectors with `kept_indices`.

For more on the embedder interfaces, see
[Using your own embeddings](../workflows/embeddings.md#using-your-own-embeddings) and the
[API reference](../api/embeddings.md).
