/** One button of the suggestion row: its text, and the user message that a click sends. */
export interface Suggestion {
    label: string;
    prompt: string;
}

// Each prompt names a task without details, so the agent asks for them.
export const TASK_SUGGESTIONS: Suggestion[] = [
    { label: 'Analyze the dataset in depth', prompt: 'Analyze the dataset in more depth.' },
    { label: 'Select samples', prompt: 'I want to select samples.' },
    { label: 'Find and tag samples', prompt: 'I want to find samples and tag them.' },
    { label: 'Ask about the docs', prompt: 'I have a question about LightlyStudio.' }
];
