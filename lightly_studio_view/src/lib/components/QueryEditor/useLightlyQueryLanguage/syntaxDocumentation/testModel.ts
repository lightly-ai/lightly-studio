import { vi } from 'vitest';

export interface WordAtPosition {
    word: string;
    startColumn: number;
    endColumn: number;
}

export interface MakeModelParams {
    text: string;
    wordAtPosition: WordAtPosition | null;
    includeGetValue?: boolean;
    includeGetOffsetAt?: boolean;
    includeGetValueInRange?: boolean;
}

/** Build a minimal Monaco-like model for syntax-documentation unit tests. */
export function makeSyntaxDocModel(params: MakeModelParams) {
    const model: Record<string, unknown> = {
        getWordAtPosition: vi.fn(() => params.wordAtPosition)
    };

    if (params.includeGetValue) {
        model.getValue = vi.fn(() => params.text);
    }

    if (params.includeGetOffsetAt) {
        model.getOffsetAt = vi.fn((pos: { lineNumber: number; column: number }) => pos.column - 1);
    }

    if (params.includeGetValueInRange) {
        model.getValueInRange = vi.fn((range: { startColumn: number; endColumn: number }) =>
            params.text.slice(range.startColumn - 1, range.endColumn - 1)
        );
    }

    return model;
}
