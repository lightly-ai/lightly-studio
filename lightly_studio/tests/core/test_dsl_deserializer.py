from lightly_studio.core.dataset_query import AND, ImageSampleField, ObjectDetectionQuery
from lightly_studio.core.dataset_query.dsl_deserializer import DSLDeserializer


def test_deserialize_complex_query() -> None:
    # Example JSON that would be sent from the frontend/Langium
    # Represents: "width > 100 AND object_detection(label == 'car' AND width < 50)"
    query_json = {
        "kind": "AND",
        "terms": [
            {
                "kind": "COMPARISON",
                "field": "width",
                "operator": ">",
                "value": 100,
            },
            {
                "kind": "ANNOTATION_QUERY",
                "annotation_type": "object_detection",
                "criterion": {
                    "kind": "AND",
                    "terms": [
                        {
                            "kind": "COMPARISON",
                            "field": "label",
                            "operator": "==",
                            "value": "car",
                        },
                        {
                            "kind": "COMPARISON",
                            "field": "width",
                            "operator": "<",
                            "value": 50,
                        },
                    ],
                },
            },
        ],
    }

    deserializer = DSLDeserializer(sample_type="image")
    expression = deserializer.deserialize(query_json)

    # Verify the structure
    assert isinstance(expression, AND)
    assert len(expression.terms) == 2

    # Verify first term (ImageSampleField.width > 100)
    # The first term's SQL representation should contain the comparison
    sql_expr = expression.terms[0].get()
    # Check that it's a binary expression and the right side value is 100
    assert sql_expr.right.value == 100

    # Verify second term (ObjectDetectionQuery.match(...))
    # It returns an ObjectDetectionMatchExpression (which is a dataclass)
    from lightly_studio.core.dataset_query.object_detection_expression import (
        ObjectDetectionMatchExpression,
    )

    assert isinstance(expression.terms[1], ObjectDetectionMatchExpression)
