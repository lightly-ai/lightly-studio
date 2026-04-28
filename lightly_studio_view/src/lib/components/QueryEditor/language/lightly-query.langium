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
  SampleAnd<isImage> ({BooleanExpression.children+=current} operator='or' children+=SampleAnd<isImage> ('or' children+=SampleAnd<isImage>)*)?
    | {BooleanExpression} operator='or' '(' children+=Sample<isImage> (',' children+=Sample<isImage>)+ ')';

SampleAnd<isImage> returns Expression:
  SampleUnary<isImage> ({BooleanExpression.children+=current} operator='and' children+=SampleUnary<isImage> ('and' children+=SampleUnary<isImage>)*)?
    | {BooleanExpression} operator='and' '(' children+=Sample<isImage> (',' children+=Sample<isImage>)+ ')';

SampleUnary<isImage> returns Expression:
  '(' Sample<isImage> ')'
    | {NotExpression} 'not' expression=SampleUnary<isImage>
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
  ObjectDetectionAnd ({BooleanExpression.children+=current} operator='or' children+=ObjectDetectionAnd ('or' children+=ObjectDetectionAnd)*)?
    | {BooleanExpression} operator='or' '(' children+=ObjectDetection (',' children+=ObjectDetection)+ ')';

ObjectDetectionAnd returns Expression:
  ObjectDetectionUnary ({BooleanExpression.children+=current} operator='and' children+=ObjectDetectionUnary ('and' children+=ObjectDetectionUnary)*)?
    | {BooleanExpression} operator='and' '(' children+=ObjectDetection (',' children+=ObjectDetection)+ ')';

ObjectDetectionUnary returns Expression:
  '(' ObjectDetection ')'
    | {NotExpression} 'not' expression=ObjectDetectionUnary
    | ObjectDetectionComparison;

ObjectDetectionComparison returns ComparisonExpression:
  ObjectDetectionFieldReference {ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=Literal;

ObjectDetectionFieldReceiver returns string:
  'ObjectDetection' | 'ObjectDetectionField';

ObjectDetectionFieldReference returns Expression:
  {FieldReference} name=ObjectDetectionFieldName
    | {QualifiedFieldReference} receiver=ObjectDetectionFieldReceiver '.' member=ObjectDetectionFieldName;

AnnotationQuery returns Expression:
  {FunctionCall} name='object_detection' '(' args+=ObjectDetection ')';

TagInExpression returns Expression:
  {TagInExpression} 'tags.contains(' tag_name=StringLiteral ')' |
    {TagInExpression} tag_name=StringLiteral 'in' 'tags';

ImageFieldReceiver returns string:
  'Image' | 'ImageSampleField';

VideoFieldReceiver returns string:
  'Video' | 'VideoSampleField';

ImageIntFieldName returns string:
  'height' | 'width';

ImageStringFieldName returns string:
  'file_name' | 'file_path_abs';

ImageDateTimeFieldName returns string:
  'created_at';

VideoIntFieldName returns string:
  'height' | 'width';

VideoOrdinalFloatFieldName returns string:
  'fps';

VideoEqualityFloatFieldName returns string:
  'duration_s';

VideoStringFieldName returns string:
  'file_name' | 'file_path_abs';

ObjectDetectionFieldName returns string:
  'height' | 'label' | 'width' | 'x' | 'y';

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

hidden terminal WS: /\s+/;
hidden terminal SL_COMMENT: /#[^\n\r]*/;
