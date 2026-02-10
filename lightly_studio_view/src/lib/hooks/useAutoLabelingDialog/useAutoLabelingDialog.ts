import { writable } from 'svelte/store';

const isAutoLabelingDialogOpen = writable(false);

export function useAutoLabelingDialog() {
	const openAutoLabelingDialog = () => {
		isAutoLabelingDialogOpen.set(true);
	};

	const closeAutoLabelingDialog = () => {
		isAutoLabelingDialogOpen.set(false);
	};

	return {
		isAutoLabelingDialogOpen,
		openAutoLabelingDialog,
		closeAutoLabelingDialog
	};
}
