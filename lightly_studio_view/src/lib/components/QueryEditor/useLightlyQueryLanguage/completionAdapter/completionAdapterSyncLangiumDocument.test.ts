import { describe, expect, it, vi } from 'vitest';

vi.mock('monaco-editor', () => ({}));

vi.mock('langium', async (importOriginal) => {
    const actual = await importOriginal<typeof import('langium')>();
    return {
        ...actual,
        URI: {
            ...actual.URI,
            parse: (value: string) => ({ toString: () => value })
        }
    };
});

describe('syncLangiumDocument', () => {
    it('rebuilds and returns document for model uri/text', async () => {
        const { syncLangiumDocument } = await import('./completionAdapterSyncLangiumDocument');
        const deleteDocument = vi.fn();
        const createDocument = vi.fn((uri: { toString: () => string }, text: string) => ({
            uri,
            textDocument: { uri: uri.toString() },
            text
        }));
        const build = vi.fn().mockResolvedValue(undefined);
        const model = {
            uri: { toString: () => 'inmemory://model/1' },
            getValue: () => 'width > 100'
        };
        const services = {
            shared: {
                workspace: {
                    LangiumDocuments: { deleteDocument, createDocument },
                    DocumentBuilder: { build }
                }
            }
        };

        const doc = await syncLangiumDocument(model as never, services as never);
        expect(deleteDocument).toHaveBeenCalledOnce();
        expect(createDocument).toHaveBeenCalledWith(expect.anything(), 'width > 100');
        expect(build).toHaveBeenCalledWith([doc], { validation: false });
        expect(doc.textDocument.uri).toBe('inmemory://model/1');
    });
});
