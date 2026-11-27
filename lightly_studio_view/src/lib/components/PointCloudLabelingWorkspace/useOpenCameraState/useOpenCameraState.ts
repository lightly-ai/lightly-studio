import { fromStore, writable } from 'svelte/store';
import type { HistoryMode, WorkspaceOptions } from '../workspaceOptions';

type OpenCameraOptions = Pick<WorkspaceOptions, 'openCamera' | 'onOpenCameraChange'>;

/**
 * Gives the open camera of the enlarged camera dialog.
 *
 * A host that passes `onOpenCameraChange` owns the open camera, for example in its URL. Without
 * it, the workspace keeps the open camera itself, so the dialog works in every configuration.
 */
export function useOpenCameraState(getOptions: () => OpenCameraOptions) {
    const localOpenCamera = fromStore(writable<string | undefined>(undefined));

    return {
        get openCamera() {
            const { openCamera, onOpenCameraChange } = getOptions();
            return onOpenCameraChange ? openCamera : localOpenCamera.current;
        },
        setOpenCamera(camera: string | undefined, historyMode: HistoryMode) {
            const { onOpenCameraChange } = getOptions();
            if (onOpenCameraChange) onOpenCameraChange(camera, historyMode);
            else localOpenCamera.current = camera;
        }
    };
}
