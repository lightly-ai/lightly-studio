import { detectScopeAt } from './detectScopeAt';

interface MaskedQuery {
    code: string;
    blocked: boolean;
}

interface MetadataQueryContextParams {
    text: string;
    offset: number;
}

/** Identify supported metadata completions at the start of the current word. */
export function getMetadataQueryContext({
    text,
    offset
}: MetadataQueryContextParams): 'field' | 'boolean' | undefined {
    const { code, blocked } = maskLiteralsAndComments(text.slice(0, offset));
    const scope = detectScopeAt(code, code.length);
    if (blocked || (scope !== 'image' && scope !== 'video')) return undefined;
    if (/\bmetadata\s*\[\s*""\s*\]\s*(?:!=|(?<![<>=!])=)\s*$/i.test(code)) {
        return 'boolean';
    }
    if (/(?:^|video:|\(|\b(?:AND|OR|NOT))\s*$/i.test(code)) return 'field';
    return undefined;
}

/** Mask string contents and comments so they cannot introduce query syntax. */
function maskLiteralsAndComments(text: string): MaskedQuery {
    let quote: string | undefined;
    let comment = false;
    let code = '';
    for (let i = 0; i < text.length; i++) {
        const character = text[i];
        if (comment && character !== '\n' && character !== '\r') continue;
        comment = false;

        if (quote && character === '\\') {
            i++;
            continue;
        }
        if (quote && character !== quote) continue;
        if (quote) {
            quote = undefined;
            code += '""';
            continue;
        }
        if (character === '#') {
            comment = true;
            continue;
        }
        if (character === '"' || character === "'") {
            quote = character;
            continue;
        }
        code += character;
    }
    return { code, blocked: quote !== undefined || comment };
}
