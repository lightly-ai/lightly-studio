import Box from '@lucide/svelte/icons/box';
import FileUp from '@lucide/svelte/icons/file-up';
import SquareDashed from '@lucide/svelte/icons/square-dashed';
import type { LabelingModelView } from '$lib/api/lightly_studio_local';
import type { SelectItem } from '$lib/components/Select/Select.svelte';

type AutoLabelModel = LabelingModelView & { runsIn: 'browser' | 'server' };

export const LOAD_MODEL_FILE_VALUE = '__load_model_file__';

const TASKS = {
    object_detection: { label: 'Object detection', icon: Box },
    instance_segmentation: { label: 'Instance segmentation', icon: SquareDashed }
} as const;
const RUNS_IN_LABELS = { browser: 'Browser', server: 'Server' } as const;
const BROWSER_DETECTION_GROUP = `${RUNS_IN_LABELS.browser} · ${TASKS.object_detection.label}`;

// Groups the models by where they run, so the user sees which ones use their own GPU. The
// browser group ends with an item that loads an ONNX file of the user's own model.
export const toModelSelectItems = (models: AutoLabelModel[]): SelectItem[] => {
    const toItem = (model: AutoLabelModel): SelectItem => ({
        value: model.id,
        label: model.id,
        group: `${RUNS_IN_LABELS[model.runsIn]} · ${TASKS[model.task].label}`,
        icon: TASKS[model.task].icon
    });
    const loadModelFileItem: SelectItem = {
        value: LOAD_MODEL_FILE_VALUE,
        label: 'Load model file (.onnx)…',
        group: BROWSER_DETECTION_GROUP,
        icon: FileUp
    };
    return [
        ...models.filter((model) => model.runsIn === 'browser').map(toItem),
        loadModelFileItem,
        ...models.filter((model) => model.runsIn === 'server').map(toItem)
    ];
};
