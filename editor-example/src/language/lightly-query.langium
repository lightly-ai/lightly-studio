grammar LightlyQuery

entry Query:
    expression=Expression;

Expression:
    LogicalOr;

LogicalOr infers Expression:
    LogicalAnd ({infer LogicalOr.left=current} 'OR' right=LogicalAnd)*;

LogicalAnd infers Expression:
    UnaryExpression ({infer LogicalAnd.left=current} 'AND' right=UnaryExpression)*;

UnaryExpression:
    NotExpression | ComparisonExpression;

NotExpression:
    'NOT' '(' expression=Expression ')';

ComparisonExpression:
    FieldAccess | ParenthesizedExpression;

ParenthesizedExpression:
    '(' expression=Expression ')';

FieldAccess:
    field=FieldPath operator=ComparisonOperator negated?='not'? value=Value |
    field=FieldPath '.' method=MethodCall;

FieldPath:
    base=FieldBase ('.' properties+=PropertyAccess)*;

FieldBase:
    type=FieldType | name=ID;

FieldType returns string:
    'ImageSampleField' | 'VideoSampleField' | 'SampleField';

PropertyAccess:
    name=PropertyName ('[' index=INT ']')?;

PropertyName returns string:
    'width' | 'height' | 'tags' | 'metadata' | 'predictions' |
    'created_at' | 'updated_at' | 'filename' | 'size' |
    'format' | 'path' | 'dataset_id' | 'sample_id' |
    'confidence' | 'label' | 'bbox' | 'segmentation' |
    'keypoints' | 'embedding' | 'score' | 'status' |
    'reviewed' | 'validated' | 'annotated' | ID;

MethodCall:
    method=MethodName '(' args=ArgumentList? ')';

MethodName returns string:
    'contains' | 'startswith' | 'endswith' | 'exists' |
    'is_null' | 'is_not_null' | 'in' | 'not_in' |
    'matches' | 'icontains' | ID;

ArgumentList:
    args+=Value (',' args+=Value)*;

ComparisonOperator returns string:
    '==' | '!=' | '<' | '>' | '<=' | '>=' | '=' | 'is' | 'in';

Value:
    StringValue | NumberValue | BooleanValue |
    NullValue | ListValue | DateValue;

StringValue:
    value=STRING;

NumberValue:
    value=NUMBER;

BooleanValue:
    value=('true' | 'false' | 'True' | 'False');

NullValue:
    value=('null' | 'None' | 'NULL');

ListValue:
    '[' (values+=Value (',' values+=Value)*)? ']';

DateValue:
    'date(' value=STRING ')' |
    'datetime(' value=STRING ')' |
    'timestamp(' value=NUMBER ')';

// Terminals
terminal ID: /[_a-zA-Z][\w_]*/;
terminal STRING: /"[^"]*"|'[^']*'/;
terminal NUMBER: /-?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?/;
terminal INT: /[0-9]+/;
terminal WS: /\s+/;

// Hidden terminals for comments
hidden terminal ML_COMMENT: /\/\*[\s\S]*?\*\//;
hidden terminal SL_COMMENT: /\/\/[^\n\r]*/;
hidden terminal PYTHON_COMMENT: /#[^\n\r]*/;