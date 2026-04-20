grammar DatasetQuery

entry Model:
    query=DatasetQueryExpression?;

// dataset.query().match(...).order_by(...)
DatasetQueryExpression:
    'dataset' '.' 'query' '(' ')' '.' 'match' '(' expression=Expression ')' 
    ('.' 'order_by' '(' orderBy=OrderByExpression ')')?;

// Expressions: AND(...), OR(...), NOT(...), queries, comparisons
Expression:
    LogicalFunction |
    QueryFunction |
    Comparison;

// AND(...), OR(...), NOT(...)
LogicalFunction:
    'AND' '(' args+=Expression (',' args+=Expression)+ ')' {infer AndExpression} |
    'OR' '(' args+=Expression (',' args+=Expression)+ ')' {infer OrExpression} |
    'NOT' '(' arg=Expression ')' {infer NotExpression};

// ObjectDetectionQuery.match(...), ObjectDetectionQuery.count(...), etc.
QueryFunction:
    type=QueryType '.' method=QueryMethod '(' arg=QueryArgument ')' 
    (operator=ComparisonOperator value=NUMBER)?;

QueryType returns string:
    'ObjectDetectionQuery' |
    'ClassificationQuery' |
    'InstanceSegmentationQuery';

QueryMethod returns string:
    'match' | 'count';

// ObjectDetectionField.label == "cat", ImageSampleField.width > 500
QueryArgument:
    Comparison;

Comparison:
    left=FieldAccess operator=ComparisonOperator right=Value;

FieldAccess:
    type=FieldType '.' field=ID;

FieldType returns string:
    'ObjectDetectionField' |
    'ClassificationField' |
    'ImageSampleField';

Value returns string:
    STRING | NUMBER;

// OrderByField(...).desc() or OrderByField(...).asc()
OrderByExpression:
    'OrderByField' '(' field=OrderByField ')' ('.' direction=SortDirection '(' ')')?;

OrderByField:
    FieldAccess |
    QueryFunction |
    TextSimilarity;

TextSimilarity:
    type=FieldType '.' 'text_similarity' '(' query=STRING ')';

SortDirection returns string:
    'desc' | 'asc';

ComparisonOperator returns string:
    '==' | '!=' | '>' | '<' | '>=' | '<=';

terminal ID: /[a-zA-Z_][a-zA-Z0-9_]*/;
terminal NUMBER returns number: /[0-9]+/;
terminal STRING: /"[^"]*"/;

hidden terminal WS: /\s+/;
hidden terminal ML_COMMENT: /\/\*[\s\S]*?\*\//;
hidden terminal SL_COMMENT: /\/\/[^\n\r]*/;
