/** Split comma- or newline-separated targets into unique, trimmed prompts. */
export function parseTargets(text: string): string[] {
    return [
        ...new Set(
            text
                .split(/[,\n]/)
                .map((prompt) => prompt.trim())
                .filter(Boolean)
        )
    ];
}
