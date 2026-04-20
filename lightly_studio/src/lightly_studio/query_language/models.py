"""Pydantic models for the query tree used in GUI-based querying."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Union

from pydantic import BaseModel, Field, StrictFloat, StrictInt, StrictStr
from typing_extensions import Literal, TypeAlias

if TYPE_CHECKING:
    from lightly_studio.core.dataset_query.match_expression import MatchExpression


class EqualityComparisonOperator(str, Enum):
    """Operators supported by equality-only fields."""

    EQ = "=="
    NEQ = "!="


class OrdinalComparisonOperator(str, Enum):
    """Operators supported by ordinal fields."""

    EQ = "=="
    NEQ = "!="
    LT = "<"
    GT = ">"
    LTE = "<="
    GTE = ">="


class ImageStringFieldName(str, Enum):
    """String image fields supported by the current query engine."""

    FILE_NAME = "file_name"
    FILE_PATH_ABS = "file_path_abs"


class ImageIntegerFieldName(str, Enum):
    """Integer image fields supported by the current query engine."""

    WIDTH = "width"
    HEIGHT = "height"


class ImageDatetimeFieldName(str, Enum):
    """Datetime image fields supported by the current query engine."""

    CREATED_AT = "created_at"


class VideoStringFieldName(str, Enum):
    """String video fields supported by the current query engine."""

    FILE_NAME = "file_name"
    FILE_PATH_ABS = "file_path_abs"


class VideoIntegerFieldName(str, Enum):
    """Integer video fields supported by the current query engine."""

    WIDTH = "width"
    HEIGHT = "height"


class VideoFloatFieldName(str, Enum):
    """Float video fields with full ordinal comparisons."""

    FPS = "fps"


class VideoEqualityFloatFieldName(str, Enum):
    """Float video fields limited by the current query engine to equality checks."""

    DURATION_S = "duration_s"


class AnnotationLabelFieldName(str, Enum):
    """Annotation string fields supported by the current query engine."""

    LABEL = "label"


class AnnotationGeometryFieldName(str, Enum):
    """Annotation numeric fields supported by the current query engine."""

    X = "x"
    Y = "y"
    WIDTH = "width"
    HEIGHT = "height"


class ImageStringFieldRef(BaseModel):
    """Reference to a string field on the image table."""

    table: Literal["image"] = "image"
    name: ImageStringFieldName


class ImageIntegerFieldRef(BaseModel):
    """Reference to an integer field on the image table."""

    table: Literal["image"] = "image"
    name: ImageIntegerFieldName


class ImageDatetimeFieldRef(BaseModel):
    """Reference to a datetime field on the image table."""

    table: Literal["image"] = "image"
    name: ImageDatetimeFieldName


class VideoStringFieldRef(BaseModel):
    """Reference to a string field on the video table."""

    table: Literal["video"] = "video"
    name: VideoStringFieldName


class VideoIntegerFieldRef(BaseModel):
    """Reference to an integer field on the video table."""

    table: Literal["video"] = "video"
    name: VideoIntegerFieldName


class VideoOrdinalFloatFieldRef(BaseModel):
    """Reference to an ordinal float field on the video table."""

    table: Literal["video"] = "video"
    name: VideoFloatFieldName


class VideoEqualityFloatFieldRef(BaseModel):
    """Reference to an equality-only float field on the video table."""

    table: Literal["video"] = "video"
    name: VideoEqualityFloatFieldName


class ImageTagsFieldRef(BaseModel):
    """Reference to the tags relationship on the image table."""

    table: Literal["image"] = "image"
    name: Literal["tags"] = "tags"


class VideoTagsFieldRef(BaseModel):
    """Reference to the tags relationship on the video table."""

    table: Literal["video"] = "video"
    name: Literal["tags"] = "tags"


class ClassificationLabelFieldRef(BaseModel):
    """Reference to a label field on classification annotations."""

    table: Literal["classification"] = "classification"
    name: AnnotationLabelFieldName


class ObjectDetectionLabelFieldRef(BaseModel):
    """Reference to a label field on object detection annotations."""

    table: Literal["object_detection"] = "object_detection"
    name: AnnotationLabelFieldName


class ObjectDetectionGeometryFieldRef(BaseModel):
    """Reference to a geometry field on object detection annotations."""

    table: Literal["object_detection"] = "object_detection"
    name: AnnotationGeometryFieldName


class InstanceSegmentationLabelFieldRef(BaseModel):
    """Reference to a label field on instance segmentation annotations."""

    table: Literal["instance_segmentation"] = "instance_segmentation"
    name: AnnotationLabelFieldName


class InstanceSegmentationGeometryFieldRef(BaseModel):
    """Reference to a geometry field on instance segmentation annotations."""

    table: Literal["instance_segmentation"] = "instance_segmentation"
    name: AnnotationGeometryFieldName


StringFieldRef: TypeAlias = Annotated[
    Union[ImageStringFieldRef, VideoStringFieldRef],
    Field(discriminator="table"),
]
IntegerFieldRef: TypeAlias = Annotated[
    Union[ImageIntegerFieldRef, VideoIntegerFieldRef],
    Field(discriminator="table"),
]
DatetimeFieldRef: TypeAlias = Annotated[
    ImageDatetimeFieldRef,
    Field(discriminator="table"),
]
OrdinalFloatFieldRef: TypeAlias = Annotated[
    VideoOrdinalFloatFieldRef,
    Field(discriminator="table"),
]
EqualityFloatFieldRef: TypeAlias = Annotated[
    VideoEqualityFloatFieldRef,
    Field(discriminator="table"),
]
TagsFieldRef: TypeAlias = Annotated[
    Union[ImageTagsFieldRef, VideoTagsFieldRef],
    Field(discriminator="table"),
]
ClassificationLabelFieldRefType: TypeAlias = Annotated[
    ClassificationLabelFieldRef,
    Field(discriminator="table"),
]
AnnotationLabelFieldRef: TypeAlias = Annotated[
    Union[
        ClassificationLabelFieldRef,
        ObjectDetectionLabelFieldRef,
        InstanceSegmentationLabelFieldRef,
    ],
    Field(discriminator="table"),
]
ObjectDetectionExprField: TypeAlias = Annotated[
    Union[ObjectDetectionLabelFieldRef, ObjectDetectionGeometryFieldRef],
    Field(discriminator="table"),
]
InstanceSegmentationExprField: TypeAlias = Annotated[
    Union[InstanceSegmentationLabelFieldRef, InstanceSegmentationGeometryFieldRef],
    Field(discriminator="table"),
]
AnnotationGeometryFieldRef: TypeAlias = Annotated[
    Union[ObjectDetectionGeometryFieldRef, InstanceSegmentationGeometryFieldRef],
    Field(discriminator="table"),
]


class StringExpr(BaseModel):
    """Leaf node for equality comparisons on string sample fields."""

    type: Literal["string_expr"] = "string_expr"
    field: StringFieldRef
    operator: EqualityComparisonOperator
    value: StrictStr


class IntegerExpr(BaseModel):
    """Leaf node for ordinal comparisons on integer sample fields."""

    type: Literal["integer_expr"] = "integer_expr"
    field: IntegerFieldRef
    operator: OrdinalComparisonOperator
    value: StrictInt


class DatetimeExpr(BaseModel):
    """Leaf node for ordinal comparisons on datetime sample fields."""

    type: Literal["datetime_expr"] = "datetime_expr"
    field: DatetimeFieldRef
    operator: OrdinalComparisonOperator
    value: datetime


class OrdinalFloatExpr(BaseModel):
    """Leaf node for ordinal comparisons on float sample fields."""

    type: Literal["ordinal_float_expr"] = "ordinal_float_expr"
    field: OrdinalFloatFieldRef
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


class EqualityFloatExpr(BaseModel):
    """Leaf node for equality comparisons on equality-only float sample fields."""

    type: Literal["equality_float_expr"] = "equality_float_expr"
    field: EqualityFloatFieldRef
    operator: EqualityComparisonOperator
    value: StrictInt | StrictFloat


class TagsContainsExpr(BaseModel):
    """Leaf node checking if a sample has a specific tag."""

    type: Literal["tags_contains_expr"] = "tags_contains_expr"
    field: TagsFieldRef
    tag_name: str


class AnnotationLabelExpr(BaseModel):
    """Criterion for equality comparisons on annotation labels."""

    type: Literal["annotation_label_expr"] = "annotation_label_expr"
    field: AnnotationLabelFieldRef
    operator: EqualityComparisonOperator
    value: StrictStr


class AnnotationGeometryExpr(BaseModel):
    """Criterion for ordinal comparisons on annotation geometry."""

    type: Literal["annotation_geometry_expr"] = "annotation_geometry_expr"
    field: AnnotationGeometryFieldRef
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


ObjectDetectionExpr: TypeAlias = Annotated[
    Union[AnnotationLabelExpr, AnnotationGeometryExpr],
    Field(discriminator="type"),
]
InstanceSegmentationExpr: TypeAlias = Annotated[
    Union[AnnotationLabelExpr, AnnotationGeometryExpr],
    Field(discriminator="type"),
]


class ClassificationMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching classification annotation."""

    type: Literal["classification_match_expr"] = "classification_match_expr"
    criteria: list[AnnotationLabelExpr] = Field(min_length=1)


class ObjectDetectionMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching object detection annotation."""

    type: Literal["object_detection_match_expr"] = "object_detection_match_expr"
    criteria: list[ObjectDetectionExpr] = Field(min_length=1)


class InstanceSegmentationMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching instance segmentation annotation."""

    type: Literal["instance_segmentation_match_expr"] = "instance_segmentation_match_expr"
    criteria: list[InstanceSegmentationExpr] = Field(min_length=1)


class AndExpr(BaseModel):
    """Boolean AND of multiple query nodes."""

    type: Literal["and"] = "and"
    children: list[MatchExpr] = Field(min_length=1)


class OrExpr(BaseModel):
    """Boolean OR of multiple query nodes."""

    type: Literal["or"] = "or"
    children: list[MatchExpr] = Field(min_length=1)


class NotExpr(BaseModel):
    """Boolean NOT of a single query node."""

    type: Literal["not"] = "not"
    child: MatchExpr


MatchExpr: TypeAlias = Annotated[
    Union[
        StringExpr,
        IntegerExpr,
        DatetimeExpr,
        OrdinalFloatExpr,
        EqualityFloatExpr,
        TagsContainsExpr,
        ClassificationMatchExpr,
        ObjectDetectionMatchExpr,
        InstanceSegmentationMatchExpr,
        AndExpr,
        OrExpr,
        NotExpr,
    ],
    Field(discriminator="type"),
]

AndExpr.model_rebuild()
OrExpr.model_rebuild()
NotExpr.model_rebuild()


class QueryTree(BaseModel):
    """Top-level model representing a complete query tree."""

    root: MatchExpr

    def to_match_expression(self) -> MatchExpression:
        """Translate the validated query tree to a dataset-query expression."""
        from lightly_studio.query_language.translation import to_match_expression

        return to_match_expression(self.root)
