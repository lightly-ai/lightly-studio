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

interface MaskingState {
    code: string;
    quote?: string;
    comment: boolean;
}

interface MaskCharacterParams {
    state: MaskingState;
    character: string;
}

/** Mask string contents and comments so they cannot introduce query syntax. */
function maskLiteralsAndComments(text: string): MaskedQuery {
    const state: MaskingState = { code: '', comment: false };
    for (let i = 0; i < text.length; i++) {
        const character = text[i];
        if (state.comment && character !== '\n' && character !== '\r') continue;
        state.comment = false;
        if (state.quote && character === '\\') {
            i++;
            continue;
        }
        if (state.quote) {
            maskQuotedCharacter({ state, character });
        } else {
            maskCodeCharacter({ state, character });
        }
    }
    return { code: state.code, blocked: state.quote !== undefined || state.comment };
}

/** Replace a completed string literal with an empty quoted string. */
function maskQuotedCharacter({ state, character }: MaskCharacterParams): void {
    if (character !== state.quote) return;
    state.quote = undefined;
    state.code += '""';
}

/** Preserve query syntax and enter comment or string state at delimiters. */
function maskCodeCharacter({ state, character }: MaskCharacterParams): void {
    if (character === '#') {
        state.comment = true;
    } else if (character === '"' || character === "'") {
        state.quote = character;
    } else {
        state.code += character;
    }
}
