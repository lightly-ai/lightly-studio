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
    member: string[];
    args: Expression[];
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
    expression=Expression;

Expression returns Expression:
    OrExpression;

OrExpression returns Expression:
    AndExpression ({BinaryExpression.left=current} operator='or' right=AndExpression)*;

AndExpression returns Expression:
    NotExpression ({BinaryExpression.left=current} operator='and' right=NotExpression)*;

NotExpression returns Expression:
    {NotExpression} 'not' expression=ComparisonExpression
    | ComparisonExpression;

ComparisonExpression returns Expression:
    PrimaryExpression ({ComparisonExpression.left=current} operator=('==' | '!=' | '<' | '>' | '<=' | '>=') right=PrimaryExpression)?;

PrimaryExpression returns Expression:
    '(' Expression ')'
    | FunctionCall
    | MemberCall
    | FieldReference
    | Literal;

FunctionCall returns Expression:
    {FunctionCall} name=ID '(' (args+=Expression (',' args+=Expression)*)? ')';

MemberCall returns Expression:
    {MemberCall} receiver=ID ('.' member+=ID)+ ('(' (args+=Expression (',' args+=Expression)*)? ')')?;

FieldReference returns Expression:
    {FieldReference} name=ID;

Literal returns Expression:
    NumberLiteral
    | StringLiteral
    | BooleanLiteral;

NumberLiteral returns Expression:
    {NumberLiteral} value=NUMBER;

StringLiteral returns Expression:
    {StringLiteral} value=STRING;

BooleanLiteral returns Expression:
    {BooleanLiteral} value=('true' | 'false');

terminal ID: /[_a-zA-Z][\w]*/;
terminal NUMBER returns number: /[0-9]+(\.[0-9]*)?/;
terminal STRING: /"([^"\\\n\r]|\\.)*"|'([^'\\\n\r]|\\.)*'/;

hidden terminal WS: /\s+/;
