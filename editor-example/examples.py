# Dataset Query Examples for Image Dataset Filtering
# ====================================================
# Write queries using the Python dataset.query() API

# USER STORY 1: Logical AND between annotations
# Find images with exactly 1 cat and 1 dog
dataset.query().match(
    AND(
        ObjectDetectionQuery.count(ObjectDetectionField.label == "cat") == 1,
        ObjectDetectionQuery.count(ObjectDetectionField.label == "dog") == 1
    )
)

# USER STORY 2: Logical OR between annotations
# Find images with exactly 1 cat or 1 dog
dataset.query().match(
    OR(
        ObjectDetectionQuery.count(ObjectDetectionField.label == "cat") == 1,
        ObjectDetectionQuery.count(ObjectDetectionField.label == "dog") == 1
    )
)

# USER STORY 3: Basic annotation presence
# Find images with at least one cat
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
)

# USER STORY 4: Query with metadata
# Find images with cats where width > 500 pixels
# Hover guide:
# - `dataset` -> dataset object used to start a query for the current dataset
# - `query` -> creates a query builder
# - `match` -> applies the filter expression
# - `AND` -> all nested conditions must be true
# - `ObjectDetectionQuery` -> query helper for object-detection annotations
# - `ImageSampleField.width` -> image width in pixels
dataset.query().match(
    AND(
        ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"),
        ImageSampleField.width > 500
    )
)

# USER STORY 5: Complex query with sorting
# Find images with cats in large images, sorted by cat count (descending)
dataset.query().match(
    AND(
        ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"),
        ImageSampleField.width > 500
    )
).order_by(
    OrderByField(
        ObjectDetectionQuery.count(ObjectDetectionField.label == "cat")
    ).desc()
)

# USER STORY 6: Text similarity sorting
# Find cats in large images, sorted by semantic similarity to "cat"
dataset.query().match(
    AND(
        ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"),
        ImageSampleField.width > 500
    )
).order_by(
    OrderByField(ImageSampleField.text_similarity("cat"))
)

# ========================================
# TAG AUTOCOMPLETE DEMO
# ========================================
# TRY THIS: Type the following line and press " after contains(
# You'll see autocomplete suggestions for available tags!

# Example 1: Filter by single tag
# Type: ImageSampleField.tags.contains("
# Press: " and see autocomplete suggestions
ImageSampleField.tags.contains("reviewed")

# Example 2: Combine with other conditions
ImageSampleField.width > 1024 AND ImageSampleField.tags.contains("high-quality")

# Example 3: Multiple tag conditions
AND(
    ImageSampleField.tags.contains("approved"),
    NOT(ImageSampleField.tags.contains("archived"))
)

# Available tags (hardcoded for now):
# - reviewed, needs-labeling, approved, rejected
# - high-quality, low-quality, duplicate
# - archived, test, validation, training
#
# See DYNAMIC_AUTOCOMPLETE.md for how to fetch tags from your API

# ========================================
# ADVANCED EXAMPLES
# ========================================

# Multiple conditions with grouping
dataset.query().match(
    AND(
        OR(
            ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"),
            ObjectDetectionQuery.match(ObjectDetectionField.label == "dog")
        ),
        ImageSampleField.width > 1000
    )
)

# Negation - images without cats
dataset.query().match(
    NOT(ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"))
)

# Multiple metadata filters
dataset.query().match(
    AND(
        ImageSampleField.width > 500,
        ImageSampleField.height > 300,
        ImageSampleField.created_at > "2024-01-01"
    )
)

# Annotation counting with different operators
dataset.query().match(
    ObjectDetectionQuery.count(ObjectDetectionField.label == "person") >= 3
)

dataset.query().match(
    ObjectDetectionQuery.count(ObjectDetectionField.label == "car") <= 5
)

dataset.query().match(
    ObjectDetectionQuery.count(ObjectDetectionField.label == "bicycle") == 0
)

# Complex boolean expression
dataset.query().match(
    OR(
        AND(
            ObjectDetectionQuery.match(ObjectDetectionField.label == "cat"),
            ImageSampleField.width > 500
        ),
        AND(
            ObjectDetectionQuery.match(ObjectDetectionField.label == "dog"),
            ImageSampleField.height > 300
        )
    )
)

# Sorting by field - ascending (default)
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
).order_by(
    OrderByField(ImageSampleField.width)
)

# Sorting by field - descending
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
).order_by(
    OrderByField(ImageSampleField.width).desc()
)

# Sorting by annotation count
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
).order_by(
    OrderByField(
        ObjectDetectionQuery.count(ObjectDetectionField.label == "cat")
    )
)

# Sorting by text similarity
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
).order_by(
    OrderByField(ImageSampleField.text_similarity("outdoor scene"))
)
