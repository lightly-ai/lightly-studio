import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export type ComponentGroup = {
	id: string;
	name: string;
	count: number;
	icon?: string;
};

// Mock data for component groups
const mockComponentGroups: ComponentGroup[] = [
	{ id: 'front-page', name: 'Front Page', count: 245, icon: '📄' },
	{ id: 'back-page', name: 'Back Page', count: 189, icon: '📃' },
	{ id: 'signature-page', name: 'Signature Page', count: 156, icon: '✍️' },
	{ id: 'attachment', name: 'Attachment', count: 98, icon: '📎' }
];

export const GET: RequestHandler = async () => {
	// Simulate network delay
	await new Promise((resolve) => setTimeout(resolve, 300));

	return json({
		componentGroups: mockComponentGroups
	});
};
