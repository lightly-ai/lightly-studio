grammar LightlyQuery

entry Query:
    expression=Expression;

Expression infers Expr:
    LogicalOrExpression;

LogicalOrExpression infers Expr:
    LogicalAndExpression ({infer BinaryExpr.left=current} operator='OR' right=LogicalAndExpression)*;

LogicalAndExpression infers Expr:
    UnaryExpression ({infer BinaryExpr.left=current} operator='AND' right=UnaryExpression)*;

UnaryExpression infers Expr:
    {infer UnaryExpr} operator='NOT' expression=PrimaryExpression | PrimaryExpression;

PrimaryExpression infers Expr:
    '(' expression=Expression ')' |
    FieldAccess;

FieldAccess:
    field=FieldReference (operator=ComparisonOperator negated?='not'? value=Value)? method=MethodCall?;

FieldReference:
    base=FieldType ('.' properties+=PropertyAccess)*;

FieldType:
    type=('ImageSampleField' | 'VideoSampleField' | 'SampleField');

PropertyAccess:
    name=ID ('[' index=INT ']')?;

MethodCall:
    '.' method=MethodName '(' arguments+=Value (',' arguments+=Value)* ')';

MethodName:
    method=('contains' | 'startswith' | 'endswith' | 'exists' | 'is_null' | 'is_not_null' | 'not_in' | 'matches' | 'icontains');

ComparisonOperator:
    op=('is' | 'in' | '==' | '!=' | '<=' | '>=' | '<' | '>' | '=');

Value infers Value:
    StringValue | NumberValue | BooleanValue | NullValue | ListValue | DateValue | FieldReference;

StringValue:
    value=STRING;

NumberValue:
    value=NUMBER;

BooleanValue:
    value=('true' | 'false' | 'True' | 'False');

NullValue:
    value=('null' | 'None' | 'NULL');

ListValue:
    '[' values+=Value (',' values+=Value)* ']';

DateValue:
    type=('date' | 'datetime' | 'timestamp') '(' value=STRING ')';

terminal NUMBER returns string:
    /-?\d+(\.\d+)?([eE][+-]?\d+)?/;

terminal ID: /[_a-zA-Z][\w_]*/;
terminal INT returns number: /[0-9]+/;
terminal STRING returns string: /"([^"\\]|\\.)*"|'([^'\\]|\\.)*'/;

hidden terminal WS: /\s+/;
hidden terminal COMMENT: /#[^\n\r]*/;
hidden terminal MULTILINE_COMMENT: /\/\*[\s\S]*?\*\//;
