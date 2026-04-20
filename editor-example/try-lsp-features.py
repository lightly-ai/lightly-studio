# Try These LSP Features!
# ======================
# This file demonstrates hover and autocomplete features

# TIP 1: Hover over "dataset" below to see documentation
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
)

# TIP 2: Type "dataset." and wait for autocomplete
# It will suggest the query() method

# TIP 3: Type "ObjectDetectionQuery." and wait for autocomplete
# It will suggest match() and count() methods

# TIP 4: Type "ObjectDetectionField." for field suggestions
# You'll see: label, confidence, bbox_x, bbox_y, bbox_width, bbox_height

# TIP 5: Type "ImageSampleField." for metadata field suggestions
# You'll see: width, height, created_at, file_name, text_similarity()

# TIP 6: Hover over any method or field to see its documentation

# TIP 7: After closing parenthesis, type "." to see order_by suggestion
dataset.query().match(
    ObjectDetectionQuery.match(ObjectDetectionField.label == "cat")
).order_by(
    OrderByField(ImageSampleField.width).desc()
)

# Press Ctrl+Space (Cmd+Space on Mac) anywhere to manually trigger autocomplete!
