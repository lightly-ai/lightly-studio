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
    ('video:' expression=Sample<false>);

Sample<isImage> returns Expression:
  SampleOr<isImage>;

SampleOr<isImage> returns Expression:
  SampleAnd<isImage> ({BooleanExpression.children+=current} operator=OR children+=SampleAnd<isImage> (OR children+=SampleAnd<isImage>)*)?
    | {BooleanExpression} operator=OR '(' children+=Sample<isImage> (',' children+=Sample<isImage>)+ ')';

SampleAnd<isImage> returns Expression:
  SampleUnary<isImage> ({BooleanExpression.children+=current} operator=AND children+=SampleUnary<isImage> (AND children+=SampleUnary<isImage>)*)?
    | {BooleanExpression} operator=AND '(' children+=Sample<isImage> (',' children+=Sample<isImage>)+ ')';

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

SampleIntFieldReference<isImage> returns QualifiedFieldReference:
  (<isImage> {QualifiedFieldReference} receiver=ImageFieldReceiver '.' member=ImageIntFieldName)
    | (<!isImage> {QualifiedFieldReference} receiver=VideoFieldReceiver '.' member=VideoIntFieldName);

SampleOrdinalFloatFieldReference<isImage> returns QualifiedFieldReference:
  (<!isImage> {QualifiedFieldReference} receiver=VideoFieldReceiver '.' member=VideoOrdinalFloatFieldName);

SampleEqualityFloatFieldReference<isImage> returns QualifiedFieldReference:
  (<!isImage> {QualifiedFieldReference} receiver=VideoFieldReceiver '.' member=VideoEqualityFloatFieldName);

SampleStringFieldReference<isImage> returns QualifiedFieldReference:
  (<isImage> {QualifiedFieldReference} receiver=ImageFieldReceiver '.' member=ImageStringFieldName)
    | (<!isImage> {QualifiedFieldReference} receiver=VideoFieldReceiver '.' member=VideoStringFieldName);

SampleDateTimeFieldReference<isImage> returns QualifiedFieldReference:
  (<isImage> {QualifiedFieldReference} receiver=ImageFieldReceiver '.' member=ImageDateTimeFieldName);

ObjectDetection returns Expression:
  ObjectDetectionOr;

ObjectDetectionOr returns Expression:
  ObjectDetectionAnd ({BooleanExpression.children+=current} operator=OR children+=ObjectDetectionAnd (OR children+=ObjectDetectionAnd)*)?
    | {BooleanExpression} operator=OR '(' children+=ObjectDetection (',' children+=ObjectDetection)+ ')';

ObjectDetectionAnd returns Expression:
  ObjectDetectionUnary ({BooleanExpression.children+=current} operator=AND children+=ObjectDetectionUnary (AND children+=ObjectDetectionUnary)*)?
    | {BooleanExpression} operator=AND '(' children+=ObjectDetection (',' children+=ObjectDetection)+ ')';

ObjectDetectionUnary returns Expression:
  '(' ObjectDetection ')'
    | {NotExpression} NOT expression=ObjectDetectionUnary
    | ObjectDetectionComparison;

ObjectDetectionComparison returns ComparisonExpression:
  ObjectDetectionFieldReference {ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=Literal;

ObjectDetectionFieldReceiver returns string:
  OBJECT_DETECTION_RECEIVER;

ObjectDetectionFieldReference returns Expression:
  {FieldReference} name=ObjectDetectionFieldName
    | {QualifiedFieldReference} receiver=ObjectDetectionFieldReceiver '.' member=ObjectDetectionFieldName;

AnnotationQuery returns Expression:
  {FunctionCall} name=ANNOTATION_FUNCTION '(' args+=ObjectDetection ')';

TagInExpression returns Expression:
  {TagInExpression} TAGS_CONTAINS '(' tag_name=StringLiteral ')' |
    {TagInExpression} tag_name=StringLiteral IN TAGS_KEYWORD;

ImageFieldReceiver returns string:
  IMAGE_SAMPLE_RECEIVER;

VideoFieldReceiver returns string:
  VIDEO_SAMPLE_RECEIVER;

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

ObjectDetectionFieldName returns string:
  HEIGHT | WIDTH | LABEL | X_COORD | Y_COORD;

Literal returns Expression:
  IntLiteral | FloatLiteral | StringLiteral;

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
terminal ANNOTATION_FUNCTION returns string: /\bobject_detection\b/;
terminal TAGS_CONTAINS returns string: /\btags\.contains\b/;
terminal TAGS_KEYWORD returns string: /\btags\b/;
terminal IMAGE_SAMPLE_RECEIVER returns string: /\b(ImageSampleField|Image)\b/;
terminal VIDEO_SAMPLE_RECEIVER returns string: /\b(VideoSampleField|Video)\b/;
terminal ORDINAL_FLOAT_FIELD_NAME returns string: /\bduration_s\b/;
terminal EQUALITY_FLOAT_FIELD_NAME returns string: /\bfps\b/;
terminal STRING_FIELD_NAME returns string: /\b(file_name|file_path_abs)\b/;
terminal DATE_TIME_FIELD_NAME returns string: /\bcreated_at\b/;
terminal OBJECT_DETECTION_RECEIVER returns string: /\b(ObjectDetectionField|ObjectDetection)\b/;

hidden terminal WS: /\s+/;
hidden terminal SL_COMMENT: /#[^\n\r]*/;
