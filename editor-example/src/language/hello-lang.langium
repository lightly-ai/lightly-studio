grammar HelloLang

entry Model:
    (greetings+=Greeting)*;

Greeting:
    'hello' person=Person ('!' | '.')?;

Person:
    name=ID;

terminal ID: /[_a-zA-Z][\w_]*/;
terminal WS: /\s+/;

hidden terminal ML_COMMENT: /\/\*[\s\S]*?\*\//;
hidden terminal SL_COMMENT: /\/\/[^\n\r]*/;
