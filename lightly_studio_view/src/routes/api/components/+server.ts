import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import type { Group, GroupComponent } from '../groups/+server';

// Import mock data from groups endpoint
// In a real app, this would query the database
const images = [
	'https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=400',
	'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=400',
	'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=400',
	'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400',
	'https://images.unsplash.com/photo-1473186578172-c141e6798cf4?w=400'
];

const groupNames = [
	'ID Photo',
	'Passport Documents',
	'Driver License',
	'Medical Records',
	'Bank Statements',
	'Utility Bills',
	'Receipts',
	'Business Cards',
	'Invoices',
	'Contracts',
	'Certificates',
	'Tax Documents',
	'Insurance Documents',
	'Legal Papers',
	'Property Deeds',
	'Vehicle Registration',
	'Academic Transcripts',
	'Employment Records',
	'Financial Reports',
	'Travel Documents'
];

const componentGroups = ['front page', 'back page', 'signature page', 'attachment'];

// Generate mock groups
const mockGroups: Group[] = Array.from({ length: 1000 }, (_, i) => {
	const groupIndex = i + 1;
	const numComponents = Math.floor(Math.random() * 4) + 2;
	const baseDate = new Date('2024-01-01');
	baseDate.setHours(baseDate.getHours() + groupIndex * 3);

	return {
		group_id: String(groupIndex),
		group_name: `${groupNames[i % groupNames.length]} ${Math.floor(i / groupNames.length) + 1}`,
		components: Array.from({ length: numComponents }, (_, j) => ({
			component_id: `img_${groupIndex}_${j + 1}`,
			component_type: 'image',
			component_name: `Component ${j + 1}`,
			component_group: componentGroups[j % componentGroups.length],
			thumbnail_url: images[j % images.length]
		})),
		created_at: baseDate.toISOString(),
		thumbnail_url: images[Math.floor(Math.random() * images.length)]
	};
});

export type ComponentWithGroup = GroupComponent & {
	group_id: string;
	group_name: string;
	created_at: string;
};

export const GET: RequestHandler = async ({ url }) => {
	// Simulate network delay
	await new Promise((resolve) => setTimeout(resolve, 500));

	// Get parameters
	const offset = parseInt(url.searchParams.get('offset') || '0');
	const limit = parseInt(url.searchParams.get('limit') || '10');
	const componentType = url.searchParams.get('component_type');

	// Flatten all components from all groups
	let allComponents: ComponentWithGroup[] = [];
	for (const group of mockGroups) {
		for (const component of group.components) {
			allComponents.push({
				...component,
				group_id: group.group_id,
				group_name: group.group_name,
				created_at: group.created_at
			});
		}
	}

	// Filter by component type if provided
	if (componentType) {
		allComponents = allComponents.filter((c) => c.component_group === componentType);
	}

	// Apply pagination
	const total = allComponents.length;
	const paginatedComponents = allComponents.slice(offset, offset + limit);
	const hasMore = offset + limit < total;

	return json({
		components: paginatedComponents,
		total,
		offset,
		limit,
		hasMore
	});
};
