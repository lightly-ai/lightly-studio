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
# FIELD PROPERTY AUTOCOMPLETE DEMO
# ========================================
# TRY THIS: Type the following and press "." to see available properties!

# Example 1: Type "ImageSampleField." and see autocomplete
# Available properties: width, height, tags, metadata, created_at, file_name, 
#                      file_size, format, predictions, text_similarity()
ImageSampleField.width > 1920

# Example 2: Type "VideoSampleField." and see autocomplete
# Available properties: duration, fps, width, height, frame_count, created_at, tags
VideoSampleField.duration > 60

# Example 3: Type "SampleField." and see autocomplete
# Available properties: created_at, updated_at, tags
SampleField.created_at >= date("2024-01-01")

# Example 4: Chain properties - type "ImageSampleField.tags." to see methods
# After typing the dot, you'll see: contains()
ImageSampleField.tags.contains("high-quality")

# Try it yourself: Type "VideoSampleField.tags." and see autocomplete
VideoSampleField.tags.contains("reviewed")

# Example 5: String methods - type "ImageSampleField.file_name." to see methods
# Available: startswith(), endswith(), contains(), icontains(), matches()
ImageSampleField.file_name.endswith(".png")

# Example 6: Format checking
ImageSampleField.format == "jpeg"

# Example 7: Metadata access - autocomplete works for nested fields too
ImageSampleField.metadata.confidence > 0.95

# ========================================
# PREDICTIONS & NESTED PROPERTIES
# ========================================
# Access model predictions and nested object properties

# Example 1: Access first prediction's label
# TRY THIS: Type predictions[0].label == " and see label autocomplete!
# predictions[0] gets the first prediction object
# .label accesses the label property of that prediction
# When you type the opening quote, you'll see available labels
ImageSampleField.predictions[0].label == "cat"

# Available labels (hardcoded for demo):
# - cat, dog, person, car, bicycle, motorcycle
# - airplane, bus, train, truck, bird, horse
# - sheep, cow, elephant, bear, zebra, giraffe
# See DYNAMIC_AUTOCOMPLETE.md for API integration

# Example 2: Access prediction confidence score
# Hover over "confidence" to see documentation
ImageSampleField.predictions[0].confidence > 0.95

# Example 3: Interactive label autocomplete demo
# Type this line yourself and see autocomplete when you type the quote:
# ImageSampleField.predictions[0].label == "
# Try selecting different labels from the suggestion list!

# Example 4: Filter by top prediction
# Find images where the model's top prediction is "dog" with high confidence
# TIP: Type predictions[0].label == " to see all available labels
AND(
    ImageSampleField.predictions[0].label == "dog",
    ImageSampleField.predictions[0].confidence >= 0.9
)

# Example 5: Check multiple predictions
# Find images where first prediction is cat OR second prediction is cat
# Autocomplete works for any index: predictions[0], predictions[1], etc.
OR(
    ImageSampleField.predictions[0].label == "cat",
    ImageSampleField.predictions[1].label == "cat"
)

# Example 6: Combine predictions with other filters
# High-confidence cat predictions in large images
AND(
    ImageSampleField.predictions[0].label == "cat",
    ImageSampleField.predictions[0].confidence > 0.95,
    ImageSampleField.width > 1920,
    ImageSampleField.tags.contains("validated")
)

# Example 6: Access nested metadata properties
# Metadata can have deeply nested structures
ImageSampleField.metadata.model.version == "v2.1"
ImageSampleField.metadata.processing.timestamp > "2024-01-01"
ImageSampleField.metadata.quality.score >= 8.5

# Example 7: Complex nested access
AND(
    ImageSampleField.predictions[0].bbox.x > 100,
    ImageSampleField.predictions[0].bbox.width < 500,
    ImageSampleField.metadata.camera.make == "Canon"
)

# ========================================
# OPERATOR AUTOCOMPLETE DEMO
# ========================================
# TRY THIS: Type a property followed by a space to see operator suggestions!

# Example 1: Type "ImageSampleField.width " (with space) and see operators
# You'll see: ==, !=, >, <, >=, <= with explanations
# Hover tip: Each operator shows its meaning and use case
ImageSampleField.width > 1920

# Example 2: Type "ImageSampleField.metadata.confidence " to see suggestions
# Try typing the space and selecting an operator from the list
ImageSampleField.metadata.confidence >= 0.95

# Example 3: Interactive operator selection
# Type this yourself and press space after "height":
# ImageSampleField.height 
# Select an operator and it will insert with a placeholder for the value!

# Example 4: Works with predictions too
# Type "ImageSampleField.predictions[0].confidence " and see operators
ImageSampleField.predictions[0].confidence > 0.9

# Example 5: Nested properties also work
# Type "ImageSampleField.metadata.quality.score " for operators
ImageSampleField.metadata.quality.score <= 10

# Available operators:
# == : Equal to (exact match)
# != : Not equal to (differs from)
# >  : Greater than (numeric only)
# <  : Less than (numeric only)
# >= : Greater than or equal to (inclusive)
# <= : Less than or equal to (inclusive)

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

# ========================================
# COMPLETE AUTOCOMPLETE WORKFLOW
# ========================================
# This example shows all autocomplete features working together!

# Step-by-step autocomplete demo:
# 1. Type "ImageSampleField." → see properties (width, height, tags, file_name, etc.)
# 2. Select "file_name", then type "." → see methods (startswith, endswith, contains, etc.)
# 3. Select "endswith", it inserts: endswith("") with cursor in quotes
# 4. Type the value: ".png"

ImageSampleField.file_name.endswith(".png")

# Another workflow:
# 1. Type "ImageSampleField." → autocomplete
# 2. Select "tags", type "." → see methods (contains, startswith, exists, etc.)
# 3. Select "contains", type "(" then " → see available tags
# 4. Select "high-quality"

ImageSampleField.tags.contains("high-quality")

# Complex example combining multiple autocomplete features:
AND(
    ImageSampleField.tags.contains("reviewed"),          # tags. → contains → " → tag list
    ImageSampleField.file_name.startswith("batch_"),     # file_name. → startswith
    ImageSampleField.format == "png",                     # format property
    ImageSampleField.width > 1024,                        # width property
    NOT(ImageSampleField.tags.contains("archived"))      # nested tags autocomplete
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
