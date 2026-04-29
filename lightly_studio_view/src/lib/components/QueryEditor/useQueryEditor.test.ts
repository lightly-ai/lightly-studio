import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
    register: vi.fn(),
    setMonarchTokensProvider: vi.fn(),
    defineTheme: vi.fn(),
    createModel: vi.fn(),
    editorCreate: vi.fn(),
    uriParse: vi.fn((s: string) => ({ scheme: 'inmemory', path: s, toString: () => s })),
    attachFn: vi.fn(),
    translateQueryFn: vi.fn()
}));

vi.mock('monaco-editor/esm/vs/editor/editor.worker?worker', () => ({
    default: vi.fn()
}));

vi.mock('monaco-editor', () => ({
    languages: {
        register: mocks.register,
        setMonarchTokensProvider: mocks.setMonarchTokensProvider
    },
    editor: {
        defineTheme: mocks.defineTheme,
        create: mocks.editorCreate,
        createModel: mocks.createModel
    },
    Uri: {
        parse: mocks.uriParse
    }
}));

vi.mock('./language/monarch.generated', () => ({
    default: {}
}));

vi.mock('./useLanguageService', () => ({
    useLightlyQueryLanguage: () => ({
        attach: mocks.attachFn,
        translateQuery: mocks.translateQueryFn
    })
}));

import { useQueryEditor } from './useQueryEditor';

interface DisposableMock {
    dispose: ReturnType<typeof vi.fn>;
}

describe('useQueryEditor', () => {
    let onDidChangeContent: ReturnType<typeof vi.fn>;
    let contentDisposable: DisposableMock;
    let attachDispose: ReturnType<typeof vi.fn>;
    let editorDispose: ReturnType<typeof vi.fn>;
    let modelDispose: ReturnType<typeof vi.fn>;
    let modelValue: string;

    beforeEach(() => {
        vi.clearAllMocks();

        modelValue = '';
        contentDisposable = { dispose: vi.fn() };
        attachDispose = vi.fn();
        editorDispose = vi.fn();
        modelDispose = vi.fn();
        onDidChangeContent = vi.fn(() => contentDisposable);

        mocks.createModel.mockImplementation((value: string) => {
            modelValue = value;
            return {
                getValue: () => modelValue,
                setValue: (next: string) => {
                    modelValue = next;
                },
                onDidChangeContent,
                dispose: modelDispose
            };
        });
        mocks.editorCreate.mockImplementation(() => ({
            dispose: editorDispose
        }));
        mocks.attachFn.mockImplementation(() => attachDispose);
    });

    it('seeds Monaco with the supplied value, not a hardcoded default', () => {
        const { mount } = useQueryEditor();
        const el = document.createElement('div');

        mount(el, { value: 'my custom query' });

        expect(mocks.createModel).toHaveBeenCalledOnce();
        expect(mocks.createModel).toHaveBeenCalledWith(
            'my custom query',
            'lightly-query',
            expect.anything()
        );
    });

    it('forwards readOnly to Monaco', () => {
        const { mount } = useQueryEditor();
        const el = document.createElement('div');

        mount(el, { value: '', readOnly: true });

        expect(mocks.editorCreate).toHaveBeenCalledOnce();
        expect(mocks.editorCreate).toHaveBeenCalledWith(
            el,
            expect.objectContaining({ readOnly: true })
        );
    });

    it('defaults readOnly to false when not provided', () => {
        const { mount } = useQueryEditor();
        const el = document.createElement('div');

        mount(el, { value: '' });

        expect(mocks.editorCreate).toHaveBeenCalledWith(
            el,
            expect.objectContaining({ readOnly: false })
        );
    });

    it('publishes model changes back through onChange', () => {
        const { mount } = useQueryEditor();
        const el = document.createElement('div');
        const onChange = vi.fn();

        mount(el, { value: 'initial', onChange });

        expect(onDidChangeContent).toHaveBeenCalledOnce();
        const listener = onDidChangeContent.mock.calls[0][0] as () => void;

        modelValue = 'updated by user';
        listener();

        expect(onChange).toHaveBeenCalledWith('updated by user');
    });

    it('attaches the language service to the created model', () => {
        const { mount } = useQueryEditor();
        const el = document.createElement('div');

        mount(el, { value: 'q' });

        expect(mocks.attachFn).toHaveBeenCalledOnce();
        expect(mocks.attachFn.mock.calls[0][0]).toBe(mocks.createModel.mock.results[0].value);
    });

    it('returns a cleanup that disposes editor, model, content listener, and language attach', () => {
        const { mount } = useQueryEditor();
        const el = document.createElement('div');

        const cleanup = mount(el, { value: 'q' });
        expect(typeof cleanup).toBe('function');

        cleanup();

        expect(contentDisposable.dispose).toHaveBeenCalledOnce();
        expect(attachDispose).toHaveBeenCalledOnce();
        expect(editorDispose).toHaveBeenCalledOnce();
        expect(modelDispose).toHaveBeenCalledOnce();
    });

    it('uses unique URIs across mounts so Monaco does not collide on remount', () => {
        const { mount } = useQueryEditor();
        const a = document.createElement('div');
        const b = document.createElement('div');

        mount(a, { value: 'q1' });
        mount(b, { value: 'q2' });

        const uris = mocks.uriParse.mock.calls.map((c) => c[0] as string);
        expect(uris.length).toBeGreaterThanOrEqual(2);
        expect(new Set(uris).size).toBe(uris.length);
    });

    it('exposes the language service translateQuery function', () => {
        const { translateQuery } = useQueryEditor();

        expect(translateQuery).toBe(mocks.translateQueryFn);
    });
});
