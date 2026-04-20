grammar LightlyQuery

interface Expression {}

interface BinaryExpression extends Expression {
    left: Expression;
    operator: 'and' | 'or';
    right: Expression;
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

interface BooleanLiteral extends Expression {
    value: 'true' | 'false';
}

entry Query:
    expression=SampleExpression;

SampleExpression returns Expression:
    SampleAndExpression ({BinaryExpression.left=current} operator='or' right=SampleAndExpression)*;

SampleAndExpression returns Expression:
    SampleComparisonExpression ({BinaryExpression.left=current} operator='and' right=SampleComparisonExpression)*;

SampleComparisonExpression returns Expression:
    {NotExpression} 'not' expression=SampleComparisonExpression
    | SamplePrimaryExpression ({ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=SamplePrimaryExpression)?;

SamplePrimaryExpression returns Expression:
    '(' SampleExpression ')'
    | AnnotationQuery
    | TagInExpression
    | SampleFieldReference
    | Literal;

ObjectDetectionExpression returns Expression:
    ObjectDetectionAndExpression ({BinaryExpression.left=current} operator='or' right=ObjectDetectionAndExpression)*;

ObjectDetectionAndExpression returns Expression:
    ObjectDetectionComparisonExpression ({BinaryExpression.left=current} operator='and' right=ObjectDetectionComparisonExpression)*;

ObjectDetectionComparisonExpression returns Expression:
    {NotExpression} 'not' expression=ObjectDetectionComparisonExpression
    | ObjectDetectionPrimaryExpression ({ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=ObjectDetectionPrimaryExpression)?;

ObjectDetectionPrimaryExpression returns Expression:
    '(' ObjectDetectionExpression ')'
    | ObjectDetectionFieldReference
    | Literal;

ObjectDetectionFieldReceiver returns string:
    'ObjectDetection' | 'ObjectDetectionField';

ObjectDetectionFieldReference returns Expression:
    {FieldReference} name=ObjectDetectionFieldName
    | {MemberCall} receiver=ObjectDetectionFieldReceiver '.' member=ObjectDetectionFieldName;

AnnotationQuery returns Expression:
    {FunctionCall} name='object_detection' '(' args+=ObjectDetectionExpression ')';

TagInExpression returns Expression:
    {TagInExpression} 'tags.contains(' tag_name=StringLiteral ')' |
    {TagInExpression} tag_name=StringLiteral 'in' 'tags';

SampleFieldReference returns Expression:
    {FieldReference} name=CommonSampleFieldName
    | {QualifiedFieldReference} receiver=ImageSampleFieldReceiver '.' member=ImageSampleFieldName
    | {QualifiedFieldReference} receiver=VideoSampleFieldReceiver '.' member=VideoSampleFieldName;

ImageSampleFieldReceiver returns string:
    'Image' | 'ImageSampleField';

VideoSampleFieldReceiver returns string:
    'Video' | 'VideoSampleField';

CommonSampleFieldName returns string:
    'created_at';

ImageSampleFieldName returns string:
    'file_name' | 'file_path_abs' | 'height' | 'width' | CommonSampleFieldName;

VideoSampleFieldName returns string:
    'file_name' | 'file_path_abs' | 'height' | 'width' | 'duration_s' | 'fps' | CommonSampleFieldName;

ObjectDetectionFieldName returns string:
    'height' | 'label' | 'width' | 'x' | 'y';

Literal returns Expression:
    NumberLiteral | StringLiteral | BooleanLiteral;

NumberLiteral returns Expression:
    {NumberLiteral} value=NUMBER;

StringLiteral returns Expression:
    {StringLiteral} value=STRING;

BooleanLiteral returns Expression:
    {BooleanLiteral} value=('true' | 'false');

terminal NUMBER returns number: /[0-9]+(\.[0-9]*)?/;
terminal STRING: /"([^"\\\n\r]|\\.)*"|'([^'\\\n\r]|\\.)*'/;

hidden terminal WS: /\s+/;
