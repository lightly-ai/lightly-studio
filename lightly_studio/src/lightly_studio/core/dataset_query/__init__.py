from .boolean_expression import AND, NOT, OR
from .classification_expression import ClassificationField, ClassificationQuery
from .dataset_query import DatasetQuery
from .image_sample_field import ImageSampleField
from .object_detection_expression import ObjectDetectionField, ObjectDetectionQuery
from .order_by import OrderByExpression, OrderByField
from .video_sample_field import VideoSampleField

# Single source of truth for the query interpreter and the completions endpoint.
# Keys are the names available in query expressions; values are the Python objects
# they resolve to.  Add new namespace classes or combinator functions here and
# both the interpreter and the autocomplete will pick them up automatically.
QUERY_NAMESPACE: dict[str, type] = {
    "ImageSampleField": ImageSampleField,
    "AND": AND,
    "OR": OR,
    "NOT": NOT,
}

__all__ = [
    "AND",
    "NOT",
    "OR",
    "QUERY_NAMESPACE",
    "ClassificationField",
    "ClassificationQuery",
    "DatasetQuery",
    "ImageSampleField",
    "ObjectDetectionField",
    "ObjectDetectionQuery",
    "OrderByExpression",
    "OrderByField",
    "VideoSampleField",
]
