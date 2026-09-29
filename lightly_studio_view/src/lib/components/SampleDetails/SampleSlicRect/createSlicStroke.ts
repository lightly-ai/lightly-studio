import type { SuperpixelMaskEditor } from '@lightly-ai/slic';

interface SlicStrokeProps {
    getEditor: () => SuperpixelMaskEditor | null;
    onActiveChange: (active: boolean) => void;
}

export function createSlicStroke({ getEditor, onActiveChange }: SlicStrokeProps) {
    let activeEditor: SuperpixelMaskEditor | null = null;
    const finish = () => {
        activeEditor = null;
        onActiveChange(false);
    };
    return {
        begin(point: { x: number; y: number }, blocked = false) {
            if (blocked || activeEditor) return null;
            const editor = getEditor();
            if (!editor) return null;
            const preview = editor.beginStroke(point);
            activeEditor = editor;
            onActiveChange(true);
            return preview;
        },
        extend(point: { x: number; y: number }) {
            return activeEditor?.extendStroke(point) ?? null;
        },
        commit() {
            if (!activeEditor) return null;
            const mask = activeEditor.commitStroke();
            finish();
            return mask;
        },
        cancel() {
            activeEditor?.cancelStroke();
            finish();
        }
    };
}
