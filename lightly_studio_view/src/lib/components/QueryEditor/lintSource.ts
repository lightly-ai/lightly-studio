import type { Diagnostic as CMDiagnostic } from '@codemirror/lint';
import type { EditorView } from '@codemirror/view';
import { validateQuery } from '$lib/api/lightly_studio_local';

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

export function buildLintSource(collectionId: string) {
    return function lintSource(view: EditorView): Promise<CMDiagnostic[]> {
        const text = view.state.doc.toString();

        if (debounceTimer !== null) {
            clearTimeout(debounceTimer);
        }

        return new Promise((resolve) => {
            debounceTimer = setTimeout(async () => {
                if (!text.trim()) {
                    resolve([]);
                    return;
                }

                try {
                    const { data } = await validateQuery({
                        path: { collection_id: collectionId },
                        body: { text },
                        throwOnError: true
                    });

                    const diagnostics: CMDiagnostic[] = data.diagnostics.map((d) => ({
                        from: d.start,
                        to: d.end,
                        message: d.message,
                        severity: (d.severity ?? 'error') as CMDiagnostic['severity']
                    }));

                    resolve(diagnostics);
                } catch {
                    resolve([]);
                }
            }, 300);
        });
    };
}
