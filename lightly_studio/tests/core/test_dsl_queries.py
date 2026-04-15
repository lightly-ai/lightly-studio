from lightly_studio.core.dataset_query import AND, NOT, OR
from lightly_studio.core.dataset_query.dsl_deserializer import DSLDeserializer
from lightly_studio.core.dataset_query.object_detection_expression import (
    ObjectDetectionMatchExpression,
)
from lightly_studio.core.dataset_query.tags_expression import TagsContainsExpression


def test_query_image_and_objects() -> None:
    # Represents: "(width > 100 or height > 100) and object_detection(label == 'car')"
    query_json = {
        "kind": "AND",
        "terms": [
            {
                "kind": "OR",
                "terms": [
                    {"kind": "COMPARISON", "field": "width", "operator": ">", "value": 100},
                    {"kind": "COMPARISON", "field": "height", "operator": ">", "value": 100},
                ],
            },
            {
                "kind": "ANNOTATION_QUERY",
                "annotation_type": "object_detection",
                "criterion": {
                    "kind": "COMPARISON",
                    "field": "label",
                    "operator": "==",
                    "value": "car",
                },
            },
        ],
    }

    deserializer = DSLDeserializer(sample_type="image")
    expression = deserializer.deserialize(query_json)

    assert isinstance(expression, AND)
    assert isinstance(expression.terms[0], OR)
    assert isinstance(expression.terms[1], ObjectDetectionMatchExpression)


def test_query_tags_with_or() -> None:
    # Represents: "tags.contains('dog') or tags.contains('cat')"
    query_json = {
        "kind": "OR",
        "terms": [
            {"kind": "TAGS_CONTAINS", "tag_name": "dog"},
            {"kind": "TAGS_CONTAINS", "tag_name": "cat"},
        ],
    }

    deserializer = DSLDeserializer(sample_type="image")
    expression = deserializer.deserialize(query_json)

    assert isinstance(expression, OR)
    assert isinstance(expression.terms[0], TagsContainsExpression)
    assert isinstance(expression.terms[1], TagsContainsExpression)
    assert expression.terms[0].tag_name == "dog"
    assert expression.terms[1].tag_name == "cat"


def test_query_nested_negation() -> None:
    # Represents: "not (width < 50 and not tags.contains('low_res'))"
    query_json = {
        "kind": "NOT",
        "term": {
            "kind": "AND",
            "terms": [
                {"kind": "COMPARISON", "field": "width", "operator": "<", "value": 50},
                {
                    "kind": "NOT",
                    "term": {"kind": "TAGS_CONTAINS", "tag_name": "low_res"},
                },
            ],
        },
    }

    deserializer = DSLDeserializer(sample_type="image")
    expression = deserializer.deserialize(query_json)

    assert isinstance(expression, NOT)
    assert isinstance(expression.term, AND)
    assert isinstance(expression.term.terms[1], NOT)
    assert isinstance(expression.term.terms[1].term, TagsContainsExpression)
