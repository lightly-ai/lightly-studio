import type { Scope } from './types';

/** Resolve the query scope at `offset` within `text`.
 *
 * The parser here is lightweight: it scans only the prefix up to `offset`,
 * tracks scope-changing function calls and parentheses, ignores parentheses
 * that appear inside string literals, and then resolves top-level video scope
 * by checking for a leading `video:` prefix.
 */
export function detectScopeAt(text: string, offset: number): Scope {
    const upTo = text.slice(0, offset).replace(/"([^"\\]|\\.)*"|'([^'\\]|\\.)*'/g, '""');
    type Frame = Scope | 'paren';
    const stack: Frame[] = [];
    const re = /\b(object_detection|classification)\s*\(|\(|\)/g;
    let match: RegExpExecArray | null;
    while ((match = re.exec(upTo))) {
        if (match[1] === 'object_detection' || match[1] === 'classification') {
            stack.push(match[1]);
        } else if (match[0] === '(') {
            stack.push('paren');
        } else {
            stack.pop();
        }
    }

    for (let i = stack.length - 1; i >= 0; i--) {
        const frame = stack[i];
        if (frame === 'object_detection' || frame === 'classification') return frame;
    }
    if (/^\s*video:/i.test(text)) return 'video';
    return 'image';
}
