import type { RootScope, Scope } from './types';

/** Resolve the query scope at `offset` within `text`.
 *
 * The parser here is lightweight: it scans only the prefix up to `offset`,
 * tracks scope-changing function calls and parentheses, ignores parentheses
 * that appear inside string literals. Outside of any function call, the scope
 * is `rootScope`.
 */
export function detectScopeAt(text: string, offset: number, rootScope: RootScope): Scope {
    const upTo = text.slice(0, offset).replace(/"([^"\\]|\\.)*"|'([^'\\]|\\.)*'/g, '""');
    type Frame = Scope | 'paren';
    const stack: Frame[] = [];
    const re = /\b(object_detection|classification|segmentation_mask)\s*\(|\(|\)/g;
    let match: RegExpExecArray | null;
    while ((match = re.exec(upTo))) {
        if (
            match[1] === 'object_detection' ||
            match[1] === 'classification' ||
            match[1] === 'segmentation_mask'
        ) {
            stack.push(match[1]);
        } else if (match[0] === '(') {
            stack.push('paren');
        } else {
            stack.pop();
        }
    }

    for (let i = stack.length - 1; i >= 0; i--) {
        const frame = stack[i];
        if (
            frame === 'object_detection' ||
            frame === 'classification' ||
            frame === 'segmentation_mask'
        ) {
            return frame;
        }
    }
    return rootScope;
}
