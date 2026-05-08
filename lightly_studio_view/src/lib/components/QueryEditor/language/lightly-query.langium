grammar LightlyQuery

interface Expression {
}

interface BooleanExpression extends Expression {
  operator: string;
  children: Expression[];
}

interface NotExpression extends Expression {
  expression: Expression;
}

interface ComparisonExpression extends Expression {
  left: Expression;
  operator: '==' | '!=' | '<' | '>' | '<=' | '>=';
  right: Expression;
}

interface FunctionCall extends Expression {
  name: string;
  args: Expression[];
}

interface FieldReference extends Expression {
  member: string;
}

interface TagInExpression extends Expression {
  tag_name: Expression;
}

interface NumberLiteral extends Expression {
  value: number;
}

interface StringLiteral extends Expression {
  value: string;
}

entry Query:
  (expression=Sample<true>) |
    (isVideo?='video:' expression=Sample<false>);

Sample<isImage> returns Expression:
  SampleOr<isImage>;

SampleOr<isImage> returns Expression:
  SampleAnd<isImage> ({BooleanExpression.children+=current} operator=OR children+=SampleAnd<isImage> (OR children+=SampleAnd<isImage>)*)?;

SampleAnd<isImage> returns Expression:
  SampleUnary<isImage> ({BooleanExpression.children+=current} operator=AND children+=SampleUnary<isImage> (AND children+=SampleUnary<isImage>)*)?;

SampleUnary<isImage> returns Expression:
  '(' Sample<isImage> ')'
    | {NotExpression} NOT expression=SampleUnary<isImage>
    | SampleComparison<isImage>
    | TagInExpression
    | AnnotationQuery;

SampleComparison<isImage> returns ComparisonExpression:
  SampleIntFieldReference<isImage> {ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=IntLiteral
   | SampleOrdinalFloatFieldReference<isImage> {ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=NumericLiteral
   | SampleEqualityFloatFieldReference<isImage> {ComparisonExpression.left=current} operator=('==' | '!=') right=NumericLiteral
   | SampleStringFieldReference<isImage> {ComparisonExpression.left=current} operator=('==' | '!=') right=StringLiteral
   | SampleDateTimeFieldReference<isImage> {ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=StringLiteral;

SampleIntFieldReference<isImage> returns FieldReference:
  (<isImage> {FieldReference} member=ImageIntFieldName)
    | (<!isImage> {FieldReference} member=VideoIntFieldName);

SampleOrdinalFloatFieldReference<isImage> returns FieldReference:
  (<!isImage> {FieldReference} member=VideoOrdinalFloatFieldName);

SampleEqualityFloatFieldReference<isImage> returns FieldReference:
  (<!isImage> {FieldReference} member=VideoEqualityFloatFieldName);

SampleStringFieldReference<isImage> returns FieldReference:
  (<isImage> {FieldReference} member=ImageStringFieldName)
    | (<!isImage> {FieldReference} member=VideoStringFieldName);

SampleDateTimeFieldReference<isImage> returns FieldReference:
  (<isImage> {FieldReference} member=ImageDateTimeFieldName);

ObjectDetection returns Expression:
  ObjectDetectionOr;

ObjectDetectionOr returns Expression:
  ObjectDetectionAnd ({BooleanExpression.children+=current} operator=OR children+=ObjectDetectionAnd (OR children+=ObjectDetectionAnd)*)?;

ObjectDetectionAnd returns Expression:
  ObjectDetectionUnary ({BooleanExpression.children+=current} operator=AND children+=ObjectDetectionUnary (AND children+=ObjectDetectionUnary)*)?;

ObjectDetectionUnary returns Expression:
  '(' ObjectDetection ')'
    | {NotExpression} NOT expression=ObjectDetectionUnary
    | ObjectDetectionComparison;

ObjectDetectionComparison returns ComparisonExpression:
  ObjectDetectionIntFieldReference {ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=IntLiteral
   | ObjectDetectionStringFieldReference {ComparisonExpression.left=current} operator=('==' | '!=') right=StringLiteral;

ObjectDetectionIntFieldReference returns FieldReference:
  {FieldReference} member=ObjectDetectionIntFieldName;

ObjectDetectionStringFieldReference returns FieldReference:
  {FieldReference} member=ObjectDetectionStringFieldName;

Classification returns Expression:
  ClassificationOr;

ClassificationOr returns Expression:
  ClassificationAnd ({BooleanExpression.children+=current} operator=OR children+=ClassificationAnd (OR children+=ClassificationAnd)*)?;

ClassificationAnd returns Expression:
  ClassificationUnary ({BooleanExpression.children+=current} operator=AND children+=ClassificationUnary (AND children+=ClassificationUnary)*)?;

ClassificationUnary returns Expression:
  '(' Classification ')'
    | {NotExpression} NOT expression=ClassificationUnary
    | ClassificationComparison;

ClassificationComparison returns ComparisonExpression:
  ClassificationFieldReference {ComparisonExpression.left=current} operator=('==' | '!=') right=StringLiteral;

ClassificationFieldReference returns Expression:
  {FieldReference} member=LABEL;

SegmentationMask returns Expression:
  SegmentationMaskOr;

SegmentationMaskOr returns Expression:
  SegmentationMaskAnd ({BooleanExpression.children+=current} operator=OR children+=SegmentationMaskAnd (OR children+=SegmentationMaskAnd)*)?;

SegmentationMaskAnd returns Expression:
  SegmentationMaskUnary ({BooleanExpression.children+=current} operator=AND children+=SegmentationMaskUnary (AND children+=SegmentationMaskUnary)*)?;

SegmentationMaskUnary returns Expression:
  '(' SegmentationMask ')'
    | {NotExpression} NOT expression=SegmentationMaskUnary
    | SegmentationMaskComparison;

SegmentationMaskComparison returns ComparisonExpression:
  SegmentationMaskIntFieldReference {ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=IntLiteral
   | SegmentationMaskStringFieldReference {ComparisonExpression.left=current} operator=('==' | '!=') right=StringLiteral;

SegmentationMaskIntFieldReference returns FieldReference:
  {FieldReference} member=SegmentationMaskIntFieldName;

SegmentationMaskStringFieldReference returns FieldReference:
  {FieldReference} member=SegmentationMaskStringFieldName;

AnnotationQuery returns Expression:
  {FunctionCall} name=OBJECT_DETECTION_FUNCTION '(' args+=ObjectDetection ')'
  | {FunctionCall} name=CLASSIFICATION_FUNCTION '(' args+=Classification ')'
  | {FunctionCall} name=SEGMENTATION_MASK_FUNCTION '(' args+=SegmentationMask ')';

TagInExpression returns Expression:
  {TagInExpression} tag_name=StringLiteral IN TAGS_KEYWORD;

terminal HEIGHT returns string: /\bheight\b/;
terminal WIDTH returns string: /\bwidth\b/;
terminal LABEL returns string: /\blabel\b/;
terminal X_COORD returns string: /\bx\b/;
terminal Y_COORD returns string: /\by\b/;

ImageIntFieldName returns string:
  HEIGHT | WIDTH;

ImageStringFieldName returns string:
  STRING_FIELD_NAME;

ImageDateTimeFieldName returns string:
  DATE_TIME_FIELD_NAME;

VideoIntFieldName returns string:
  HEIGHT | WIDTH;

VideoOrdinalFloatFieldName returns string:
  ORDINAL_FLOAT_FIELD_NAME;

VideoEqualityFloatFieldName returns string:
  EQUALITY_FLOAT_FIELD_NAME;

VideoStringFieldName returns string:
  STRING_FIELD_NAME;

ObjectDetectionIntFieldName returns string:
  HEIGHT | WIDTH | X_COORD | Y_COORD;

ObjectDetectionStringFieldName returns string:
  LABEL;

SegmentationMaskIntFieldName returns string:
  HEIGHT | WIDTH | X_COORD | Y_COORD;

SegmentationMaskStringFieldName returns string:
  LABEL;

NumericLiteral returns Expression:
  IntLiteral | FloatLiteral;

IntLiteral returns Expression:
  {NumberLiteral} value=INT;

FloatLiteral returns Expression:
  {NumberLiteral} value=FLOAT;

StringLiteral returns Expression:
  {StringLiteral} value=STRING;

terminal FLOAT returns number: /[0-9]+\.[0-9]*/;
terminal INT returns number: /[0-9]+/;
terminal STRING: /"([^"\\\n\r]|\\.)*"|'([^'\\\n\r]|\\.)*'/;

terminal AND: /\bAND\b/i;
terminal OR: /\bOR\b/i;
terminal NOT: /\bNOT\b/i;
terminal IN returns string: /\bIN\b/i;
terminal OBJECT_DETECTION_FUNCTION returns string: /\bobject_detection\b/;
terminal CLASSIFICATION_FUNCTION returns string: /\bclassification\b/;
terminal SEGMENTATION_MASK_FUNCTION returns string: /\bsegmentation_mask\b/;
terminal TAGS_KEYWORD returns string: /\btags\b/;
terminal ORDINAL_FLOAT_FIELD_NAME returns string: /\bduration_s\b/;
terminal EQUALITY_FLOAT_FIELD_NAME returns string: /\bfps\b/;
terminal STRING_FIELD_NAME returns string: /\b(file_name|file_path_abs)\b/;
terminal DATE_TIME_FIELD_NAME returns string: /\bcreated_at\b/;

hidden terminal WS: /\s+/;
hidden terminal SL_COMMENT: /#[^\n\r]*/;
