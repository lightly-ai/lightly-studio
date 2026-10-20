# Use Gemini Embedding 2 from OpenRouter in LightlyStudio

In this tutorial, you use a hosted embedding model in LightlyStudio. The model is
[Gemini Embedding 2](https://openrouter.ai/google/gemini-embedding-2), served by
[OpenRouter](https://openrouter.ai).

You will:

- Write an embedder that sends images and text to the OpenRouter embeddings API.
- Register it, so that LightlyStudio uses it at ingestion and in the GUI.
- Ingest raw images and explore them with the embedding plot, text search and image search.
- Change to a different OpenRouter model.

!!! example "Beta API"
    The embeddings API is in beta. Its interface may change in future releases
    without a deprecation period.

## Why use a hosted embedding model

By default, LightlyStudio computes embeddings with a small model on your machine. A hosted
model is useful when:

- You want a large model, but you do not have a GPU.
- You want to compare models from different providers with one API.

OpenRouter gives one HTTP API for embedding models from many providers. Gemini Embedding 2
is multimodal: it puts text and images in one embedding space. Thus a text query such as
"a person on a bicycle" is near the images that show it. LightlyStudio needs this for text
search.

!!! warning "Your data leaves your machine"
    The embedder sends each image and each text query to OpenRouter and to the model
    provider. Do not use a hosted model for data that must stay on your machine. Read the
    [OpenRouter privacy settings](https://openrouter.ai/settings/privacy) first.

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

## Step 2: Understand the embedder

An embedder subclasses one interface for each input it can embed. Gemini Embedding 2
embeds images and text, so the embedder subclasses four interfaces:

| Interface | Used for |
|---|---|
| `ImagePathEmbedder` | Images at ingestion |
| `ImageCropPathEmbedder` | Annotation crops at ingestion |
| `ImageBytesEmbedder` | Image search in the GUI |
| `TextEmbedder` | Text search and text axes in the GUI |

The full code is in
[`example_openrouter_embedder.py`](https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_openrouter_embedder.py).
Download it to your working directory. The next sections explain its important parts.

### The embedding space

`embedding_space_spec` gives the name and the length of the vectors. LightlyStudio
stores the name with the embeddings. Vectors with the same name must be comparable.

```python
def embedding_space_spec(self) -> ls.EmbeddingSpaceSpec:
    return ls.EmbeddingSpaceSpec(
        space_key=f"openrouter/{self._model}@{self._dimension}",
        dimension=self._dimension,
    )
```

The key contains the model and the dimension. If you change one of them, LightlyStudio
puts the new vectors in a new space, and does not mix them with the old vectors.

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

If the embedder cannot read an image, it skips the image. It does not include the
position of that image in `kept_indices`, so LightlyStudio knows which images have no
embedding.

### Batches and retries

LightlyStudio gives the embedder up to 1024 images in one call. The embedder sends them
in batches of 16 inputs. A hosted API can fail for a short time, for example with HTTP 429
(rate limit). The embedder tries the request again after a wait, so that one failure does
not stop the ingestion.

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
  The query goes to OpenRouter, and the grid shows the most similar images first. Each
  image shows its similarity to the query.
- **Image search.** Upload an image in the search field. The grid shows the images that
  are most similar to it.

## Step 5: Use a different model

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
input types of each model in `architecture.input_modalities`.

A text-only model, such as `openai/text-embedding-3-small`, cannot embed images. For such
a model, subclass only `TextEmbedder`. You can use it for the text of your samples, but
not for image search or the embedding plot of images.

If the model returns vectors of a different length than `dimension`, the embedder raises
an error that shows the received shape. Set `dimension` to that length.

!!! note "Free models"
    Models with the `:free` suffix have low rate limits, and some requests take a long
    time. The embedder tries a request again after a timeout, but a large ingestion can
    still be slow. Use a paid model for large datasets.

## Cost and limits

- **Cost.** OpenRouter charges for each input token. With Gemini Embedding 2, one image
  is 258 tokens, which is about $0.00012. The 128 images of this tutorial cost about
  $0.015, and 100,000 images cost about $12. A text query costs almost nothing. Prices
  can change, so check the [model page](https://openrouter.ai/google/gemini-embedding-2).
  You see your total cost on the [activity page](https://openrouter.ai/activity).
- **Speed.** One request with 16 images takes about one second. Thus 100,000 images take
  about two hours. For more speed, send more batches at the same time from more than one
  thread.
- **Rate limits.** OpenRouter and the provider limit the number of requests. The embedder
  waits and tries again when it receives HTTP 429.

## Conclusion

You used a hosted multimodal embedding model in LightlyStudio with one small Python class.
The same pattern works for each HTTP embedding API: subclass the interfaces for the inputs
that the API can embed, convert the inputs to the request format, and return the vectors
with `kept_indices`.

For more on the embedder interfaces, see
[Using your own embeddings](../workflows/embeddings.md#using-your-own-embeddings) and the
[API reference](../api/embeddings.md).
