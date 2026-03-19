# Search and Filter

Search helps you find visually or semantically similar samples from a text or image. Filters narrow the current collection by tags, labels, dimensions, and other numeric metadata.


## Search in GUI

On Images and Videos, the search bar sits above the grid. You can search by either of the following methods:

1. Type a text query.
2. Paste an image from your clipboard into the search bar. You can e.g. right-click an image in your browser and select `Copy image`, then click the search bar and paste it with `Ctrl+V` or `Cmd+V`.
3. Click the image button to upload an image.

Then submit the search by hitting `Enter`. The number shown on each search result is its similarity score to the current query. Click `Clear search` to remove the search query and return to the normal input state.

The screen recording below shows how to search for similar images by either using the text query "dog" or by pasting an image.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/search_filter_search_v4.mp4" type="video/mp4">
</video>

!!! note "Search requires embeddings"
    Search is available on Images and Videos when embeddings exist.

## Filter in GUI

The left sidebar combines the most common ways to narrow a collection:

- `Tags`: Click one or more tags to focus on the subset you care about, such as `labeled` or `unlabeled`.
- `Labels`: Click one or more labels to show items with those annotations.
- `Dimensions`: Use `Width` and `Height` to constrain the visible item size.
- `Extra numeric metadata`: If your collection has numeric metadata fields, they appear as additional sliders in the same area.

![Tag filters](https://storage.googleapis.com/lightly-public/studio/search_filter_tags_v2.png){ width="100%"}


For videos, the sidebar adds `Duration`. If the current video collection contains varying frame rates, it also shows `FPS`.

![Video filters](https://storage.googleapis.com/lightly-public/studio/search_filter_videos_v3.png){ width="100%" }
