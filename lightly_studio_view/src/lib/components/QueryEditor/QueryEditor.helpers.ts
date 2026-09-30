import type { QueryExprTranslationResult } from './language/query-expr-translation';
import type { RootScope } from './language/types';

/** Example query that the editor shows when no value is given. */
export const DEFAULT_QUERIES: Record<RootScope, string> = {
    image: `# Example query
width < 500
AND "reviewed" IN tags
AND object_detection(class_name = "person" AND x > 10)
`,
    video: `# Example query
duration_s > 10
AND "reviewed" IN tags
AND object_detection(class_name = "person")
`
};

/** Format translation errors as one line per error, with the position if known. */
export function formatTranslationErrors(
    result: Extract<QueryExprTranslationResult, { status: 'error' }>
): string {
    return result.errors
        .map((error) => {
            if (error.line !== undefined && error.column !== undefined) {
                return `${error.message} (line ${error.line}, column ${error.column})`;
            }
            return error.message;
        })
        .join('\n');
}
