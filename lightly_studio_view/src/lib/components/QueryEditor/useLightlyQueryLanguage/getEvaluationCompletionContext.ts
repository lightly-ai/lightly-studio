interface EvaluationCompletionContextParams {
    text: string;
    offset: number;
}
/** Distinguish the required run selector from criteria, ignoring strings and comments. */
export function getEvaluationCompletionContext({
    text,
    offset
}: EvaluationCompletionContextParams): 'selector' | 'run' | 'criteria' {
    const prefix = text
        .slice(0, offset)
        .replace(/#[^\r\n]*|"(?:[^"\\]|\\.)*(?:"|$)|'(?:[^'\\]|\\.)*(?:'|$)/g, ' ');
    const opening = [...prefix.matchAll(/\bsample_evaluation\s*\(/g)].at(-1);
    const body = opening ? prefix.slice(opening.index + opening[0].length) : '';
    if (/\bAND\b/.test(body)) return 'criteria';
    return /\bname\s*=/.test(body) ? 'run' : 'selector';
}
