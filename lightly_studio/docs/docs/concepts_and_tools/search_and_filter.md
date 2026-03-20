# Search and Filter

Search helps you find visually or semantically similar samples from a text or image. Filters narrow down the samples currently shown in the view by tags, labels, dimensions, and other numeric metadata.


## Search in GUI

Use the search bar above the grid to find similar samples in one of these ways:

1. Type a text query.
2. Paste an image from your clipboard into the search bar. You can e.g. right-click an image in your browser and select `Copy image`, then click the search bar and paste it with `Ctrl+V` or `Cmd+V`.
3. Click the image button to upload an image.

Then submit the search by hitting `Enter`. The number shown on each search result is its similarity score to the current query. Click the `x` button to remove the search query.

The screen recording below shows the search both by text query "dog" and by pasting an image.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/search_filter_search_v4.mp4" type="video/mp4">
</video>

!!! note "Search requires embeddings"
    Search is available only when embeddings were generated during data loading.

## Filter in GUI

The left sidebar combines the most common ways to narrow down the visible samples:

- `Tags`: Click one or more tags to focus on the subset you care about, such as `labeled` or `unlabeled`.
- `Labels`: Click one or more labels to show items with those annotations.
- `Dimensions`: Use `Width` and `Height` to constrain the visible item size.
- `Metadata`: If numeric metadata fields are available, they appear as additional sliders in the same area.

![Tag filters](https://storage.googleapis.com/lightly-public/studio/search_filter_tags_v3.png){ width="100%"}


For videos, the sidebar adds `Duration`. If the videos in the current view contain varying frame rates, it also shows `FPS`.

![Video filters](https://storage.googleapis.com/lightly-public/studio/search_filter_videos_v4.jpg){ width="100%" }
