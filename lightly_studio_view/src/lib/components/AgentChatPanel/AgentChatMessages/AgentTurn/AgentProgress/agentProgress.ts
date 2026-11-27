// A reasoning summary often starts each thought with a bold line, for example
// "**Planning the selection**".
const HEADING_LINE = /^\s*\*\*(.+?)\*\*\s*$/gm;
const SECONDS_PER_MINUTE = 60;
const MS_PER_SECOND = 1000;

/** Gets the heading of the newest thought in a reasoning text, if the text has headings. */
export function latestReasoningHeading(text: string): string | undefined {
    const headings = [...text.matchAll(HEADING_LINE)].map((match) => match[1].trim());
    return headings.at(-1) || undefined;
}

/** Removes the markdown bold markers, so the reasoning reads as plain text. */
export function toPlainReasoning(text: string): string {
    return text.replaceAll('**', '').trim();
}

/** Formats a duration for a person, for example "7s" or "1m 05s". */
export function formatDuration(milliseconds: number): string {
    const totalSeconds = Math.max(0, Math.round(milliseconds / MS_PER_SECOND));
    const minutes = Math.floor(totalSeconds / SECONDS_PER_MINUTE);
    const seconds = totalSeconds % SECONDS_PER_MINUTE;
    if (!minutes) return `${seconds}s`;
    return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
}
