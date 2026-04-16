import { HighlightStyle, LRLanguage, LanguageSupport, syntaxHighlighting } from '@codemirror/language';
import { styleTags, tags as t } from '@lezer/highlight';
// @ts-expect-error generated JS file without types
import { parser } from './query-language.js';

export const queryLanguage = LRLanguage.define({
    parser: parser.configure({
        props: [
            styleTags({
                'or and not has_tag has_annotation contains _in BoolTrue BoolFalse': t.keyword,
                Identifier: t.name,
                String: t.string,
                Number: t.number,
                CmpOpToken: t.operator,
                '( )': t.paren,
                '[ ]': t.squareBracket
            })
        ]
    }),
    languageData: {}
});

const queryHighlightStyle = HighlightStyle.define([
    { tag: [t.keyword, t.operatorKeyword], color: 'hsl(332 79% 72%)', fontWeight: '600' },
    { tag: t.operator, color: 'hsl(18 94% 71%)', fontWeight: '700' },
    { tag: t.name, color: 'hsl(195 88% 74%)' },
    { tag: t.string, color: 'hsl(152 70% 68%)' },
    { tag: t.number, color: 'hsl(44 95% 70%)' },
    { tag: t.bool, color: 'hsl(262 85% 78%)', fontWeight: '600' },
    { tag: [t.paren, t.squareBracket], color: 'hsl(var(--muted-foreground))' }
]);

export function queryEditorLanguage(): LanguageSupport {
    return new LanguageSupport(queryLanguage, [syntaxHighlighting(queryHighlightStyle)]);
}
