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

interface MemberCall extends Expression {
  receiver: string;
  member: string;
  args: Expression[];
}

interface QualifiedFieldReference extends Expression {
  receiver: string;
  member: string;
}

interface TagInExpression extends Expression {
  tag_name: Expression;
}

interface FieldReference extends Expression {
  name: string;
}

interface NumberLiteral extends Expression {
  value: number;
}

interface StringLiteral extends Expression {
  value: string;
}

entry Query:
  (expression=Sample<true>) |
    (prefix=VideoQueryPrefix expression=Sample<false>);

Sample<isImage> returns Expression:
  SampleOr<isImage>;

SampleOr<isImage> returns Expression:
  SampleAnd<isImage> ({BooleanExpression.children+=current} operator=OrOperator children+=SampleAnd<isImage> (OrOperator children+=SampleAnd<isImage>)*)?
    | {BooleanExpression} operator=OrOperator '(' children+=Sample<isImage> (',' children+=Sample<isImage>)+ ')';

SampleAnd<isImage> returns Expression:
  SampleUnary<isImage> ({BooleanExpression.children+=current} operator=AndOperator children+=SampleUnary<isImage> (AndOperator children+=SampleUnary<isImage>)*)?
    | {BooleanExpression} operator=AndOperator '(' children+=Sample<isImage> (',' children+=Sample<isImage>)+ ')';

SampleUnary<isImage> returns Expression:
  '(' Sample<isImage> ')'
    | {NotExpression} NotOperator expression=SampleUnary<isImage>
    | SampleComparison<isImage>
    | TagInExpression
    | AnnotationQuery;

SampleComparison<isImage> returns ComparisonExpression:
  SampleFieldReference<isImage> {ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=Literal;

SampleFieldReference<isImage> returns QualifiedFieldReference:
  (<isImage> {QualifiedFieldReference} receiver=ImageSampleFieldReceiver '.' member=ImageSampleFieldName)
    | (<!isImage> {QualifiedFieldReference} receiver=VideoSampleFieldReceiver '.' member=VideoSampleFieldName);

ObjectDetection returns Expression:
  ObjectDetectionOr;

ObjectDetectionOr returns Expression:
  ObjectDetectionAnd ({BooleanExpression.children+=current} operator=OrOperator children+=ObjectDetectionAnd (OrOperator children+=ObjectDetectionAnd)*)?
    | {BooleanExpression} operator=OrOperator '(' children+=ObjectDetection (',' children+=ObjectDetection)+ ')';

ObjectDetectionAnd returns Expression:
  ObjectDetectionUnary ({BooleanExpression.children+=current} operator=AndOperator children+=ObjectDetectionUnary (AndOperator children+=ObjectDetectionUnary)*)?
    | {BooleanExpression} operator=AndOperator '(' children+=ObjectDetection (',' children+=ObjectDetection)+ ')';

ObjectDetectionUnary returns Expression:
  '(' ObjectDetection ')'
    | {NotExpression} NotOperator expression=ObjectDetectionUnary
    | ObjectDetectionComparison;

ObjectDetectionComparison returns ComparisonExpression:
  ObjectDetectionFieldReference {ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=Literal;

ObjectDetectionFieldReceiver returns string:
  OBJECT_DETECTION_RECEIVER;

ObjectDetectionFieldReference returns Expression:
  {FieldReference} name=ObjectDetectionFieldName
    | {QualifiedFieldReference} receiver=ObjectDetectionFieldReceiver '.' member=ObjectDetectionFieldName;

AnnotationQuery returns Expression:
  {FunctionCall} name=AnnotationFunctionName '(' args+=ObjectDetection ')';

TagInExpression returns Expression:
  {TagInExpression} TagsContainsAccessor '(' tag_name=StringLiteral ')' |
    {TagInExpression} tag_name=StringLiteral InOperator TagsKeyword;

VideoQueryPrefix returns string:
  VIDEO_QUERY_PREFIX;

AndOperator returns string:
  BOOLEAN_AND;

OrOperator returns string:
  BOOLEAN_OR;

NotOperator returns string:
  BOOLEAN_NOT;

InOperator returns string:
  BOOLEAN_IN;

AnnotationFunctionName returns string:
  ANNOTATION_FUNCTION;

TagsContainsAccessor returns string:
  TAGS_CONTAINS;

TagsKeyword returns string:
  TAGS_KEYWORD;

ImageSampleFieldReceiver returns string:
  IMAGE_SAMPLE_RECEIVER;

VideoSampleFieldReceiver returns string:
  VIDEO_SAMPLE_RECEIVER;

CommonSampleFieldName returns string:
  COMMON_SAMPLE_FIELD_NAME;

ImageSampleFieldName returns string:
  IMAGE_SAMPLE_FIELD_NAME | CommonSampleFieldName;

VideoSampleFieldName returns string:
  VIDEO_SAMPLE_FIELD_NAME | CommonSampleFieldName;

ObjectDetectionFieldName returns string:
  OBJECT_DETECTION_FIELD_NAME;

Literal returns Expression:
  NumberLiteral | StringLiteral;

NumberLiteral returns Expression:
  {NumberLiteral} value=NUMBER;

StringLiteral returns Expression:
  {StringLiteral} value=STRING;

terminal NUMBER returns number: /[0-9]+(\.[0-9]*)?/;
terminal STRING: /"([^"\\\n\r]|\\.)*"|'([^'\\\n\r]|\\.)*'/;
terminal VIDEO_QUERY_PREFIX returns string: /video:/;
terminal BOOLEAN_AND returns string: /and\b/;
terminal BOOLEAN_OR returns string: /or\b/;
terminal BOOLEAN_NOT returns string: /not\b/;
terminal BOOLEAN_IN returns string: /in\b/;
terminal ANNOTATION_FUNCTION returns string: /object_detection\b/;
terminal TAGS_CONTAINS returns string: /tags\.contains\b/;
terminal TAGS_KEYWORD returns string: /tags\b/;
terminal IMAGE_SAMPLE_RECEIVER returns string: /(ImageSampleField|Image)\b/;
terminal VIDEO_SAMPLE_RECEIVER returns string: /(VideoSampleField|Video)\b/;
terminal COMMON_SAMPLE_FIELD_NAME returns string: /created_at\b/;
terminal IMAGE_SAMPLE_FIELD_NAME returns string: /(file_name|file_path_abs|height|width)\b/;
terminal VIDEO_SAMPLE_FIELD_NAME returns string: /(file_name|file_path_abs|height|width|duration_s|fps)\b/;
terminal OBJECT_DETECTION_RECEIVER returns string: /(ObjectDetectionField|ObjectDetection)\b/;
terminal OBJECT_DETECTION_FIELD_NAME returns string: /(height|label|width|x|y)\b/;

hidden terminal WS: /\s+/;
hidden terminal SL_COMMENT: /#[^\n\r]*/;
