import { describe, expect, it } from 'vitest';
import { highlightPython } from './highlightPython';

describe('highlightPython', () => {
    it('marks keywords, strings, comments and numbers', () => {
        const tokens = highlightPython('import lightly_studio as ls  # SDK\nx = load("a#b", 2)');

        expect(tokens).toEqual([
            { kind: 'keyword', text: 'import' },
            { kind: 'plain', text: ' lightly_studio ' },
            { kind: 'keyword', text: 'as' },
            { kind: 'plain', text: ' ls  ' },
            { kind: 'comment', text: '# SDK' },
            { kind: 'plain', text: '\nx = load(' },
            { kind: 'string', text: '"a#b"' },
            { kind: 'plain', text: ', ' },
            { kind: 'number', text: '2' },
            { kind: 'plain', text: ')' }
        ]);
    });

    it('keeps the full text when the tokens are joined', () => {
        const code = 'with open("x.txt", "w") as f:\n    f.write(f"{s}\\n")\n';

        expect(
            highlightPython(code)
                .map((token) => token.text)
                .join('')
        ).toBe(code);
    });

    it('treats an f-string prefix as part of the string', () => {
        expect(highlightPython('f"{x}"')).toEqual([{ kind: 'string', text: 'f"{x}"' }]);
    });
});
