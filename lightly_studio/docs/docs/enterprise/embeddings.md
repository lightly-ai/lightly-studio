# Custom Embeddings

This guide shows how to use your own embedding model with LightlyStudio Enterprise. It is
intended for admins who add data from Python with [`ls.connect()`](connect.md). For the
embedder interfaces and code examples, see
[Using Your Own Embeddings](../workflows/embeddings.md#using-your-own-embeddings).

The enterprise instance stores the vectors that you add from Python. The embedding plot and
sampling read the stored vectors, so they work with any model. Similarity search and text
axes must embed each query while the GUI runs, so they need a remote embedder.

## Choose a Setup

=== "Remote Embedder"

    Your model runs on a server. The remote embedder embeds your data at ingestion and also
    embeds the search queries. Register it with `ls.register_default_embedder` before you add
    data. To embed images, the server must implement `ImageBytesEmbedder`.

    ![Your own model in a remote embedder](../_static/lightly_studio_enterprise_remote_embedder.svg#only-light){ width="100%" }
    ![Your own model in a remote embedder](../_static/lightly_studio_enterprise_remote_embedder_dark.svg#only-dark){ width="100%" }

    The dataset stores the URL of the server. Search then uses the same server, with no
    other registration. See
    [Serving an Embedder from a Remote Server](../workflows/embeddings.md#serving-an-embedder-from-a-remote-server).

=== "Local Embedder"

    Your model runs in the Python script. Register the local embedder with
    `ls.register_default_embedder` before you add data. It can run your model, or it can load
    vectors that you computed before.

    ![Your own model in a local embedder](../_static/lightly_studio_enterprise_local_embedder.svg#only-light){ width="100%" }
    ![Your own model in a local embedder](../_static/lightly_studio_enterprise_local_embedder_dark.svg#only-dark){ width="100%" }

    The enterprise server cannot call a local embedder. As a result, similarity search and
    text axes are not available in this setup. To use them, choose a remote embedder.

## Reach the Remote Embedder

The Python client contacts the server of the remote embedder when you register it. The
enterprise server sends each search query to it. Both must be able to reach the URL of the
server.

Each process checks the URL before it connects. If
`LIGHTLY_STUDIO_REMOTE_EMBEDDER_ALLOW_PRIVATE_URLS` is `False`, the process accepts only an
HTTPS URL that resolves to public addresses. The default is `True`, which also accepts
private addresses.
