/** One button of the suggestion row: its text, and the user message that a click sends. */
export interface Suggestion {
    label: string;
    prompt: string;
}

export const COLLECTION_OVERVIEW: Suggestion = {
    label: 'Summarize this collection',
    prompt: 'Give me a brief overview of this collection. Highlight what is worth exploring.'
};
