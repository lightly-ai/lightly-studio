/** Supply collection scope to the parser without changing the visible query. */
export function getQuerySource(value: string, sampleType?: 'image' | 'video') {
    const hasVideoPrefix = /^(?:\s|#[^\n\r]*(?:[\n\r]|$))*video:/.test(value);
    const lineOffset = sampleType === 'video' && !hasVideoPrefix ? 1 : 0;
    return { text: lineOffset ? `video:\n${value}` : value, lineOffset };
}
