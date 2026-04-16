import { LRLanguage, LanguageSupport } from '@codemirror/language';
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

export function queryEditorLanguage(): LanguageSupport {
    return new LanguageSupport(queryLanguage);
}
