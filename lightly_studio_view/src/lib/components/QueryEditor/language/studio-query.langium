grammar StudioQuery

interface Expression {}

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

interface BooleanLiteral extends Expression {
    value: 'true' | 'false';
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
    SampleFieldReference<isImage> {ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=Literal;

SampleFieldReference<isImage> returns QualifiedFieldReference:
    (<isImage> {QualifiedFieldReference} receiver=ImageSampleFieldReceiver '.' member=ImageSampleFieldName)
    | (<!isImage> {QualifiedFieldReference} receiver=VideoSampleFieldReceiver '.' member=VideoSampleFieldName);

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

ObjectDetectionFieldReference returns QualifiedFieldReference:
    {FieldReference} name=ObjectDetectionFieldName
    | {QualifiedFieldReference} receiver=ObjectDetectionFieldReceiver '.' member=ObjectDetectionFieldName;

AnnotationQuery returns Expression:
    {FunctionCall} name='object_detection' '(' args+=ObjectDetection ')';

TagInExpression returns Expression:
    {TagInExpression} 'tags.contains(' tag_name=StringLiteral ')' |
    {TagInExpression} tag_name=StringLiteral 'in' 'tags';

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
