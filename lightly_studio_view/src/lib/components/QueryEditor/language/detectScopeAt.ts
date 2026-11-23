import type { Scope } from './types';

/** Resolve the query scope at the cursor, including when the expression is incomplete. */
export function detectScopeAt(text: string, offset: number): Scope {
    const upTo = text
        .slice(0, offset)
        .replace(/"([^"\\]|\\.)*"?|'([^'\\]|\\.)*'?|#[^\n\r]*/g, (token) =>
            token.startsWith('#') ? '' : '""'
        );
    const rootScope = /^\s*video:/i.test(upTo) ? 'video' : 'image';
    const stack: Scope[] = [];
    const re =
        /\b(object_detection|classification|segmentation_mask|frame|event|sample_evaluation)\s*\(|\(|\)/g;
    let match: RegExpExecArray | null;
    while ((match = re.exec(upTo))) {
        const scope = stack.at(-1) ?? rootScope;
        if (
            match[1] === 'object_detection' ||
            match[1] === 'classification' ||
            match[1] === 'segmentation_mask' ||
            match[1] === 'sample_evaluation'
        ) {
            stack.push(match[1]);
        } else if (match[1] === 'frame' || match[1] === 'event') {
            stack.push(scope === 'video' ? match[1] : scope);
        } else if (match[0] === '(') {
            stack.push(scope);
        } else {
            stack.pop();
        }
    }

    return stack.at(-1) ?? rootScope;
}
