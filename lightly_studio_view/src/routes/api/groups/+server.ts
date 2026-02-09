import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export type GroupComponent = {
	component_id: string;
	component_type: string;
	component_name: string;
	thumbnail_url?: string;
};

export type Group = {
	group_id: string;
	group_name: string;
	components: GroupComponent[];
	created_at: string;
};

// Mock data
const mockGroups: Group[] = [
	{
		group_id: '1',
		group_name: 'ID Photo',
		components: [
			{
				component_id: 'img_001',
				component_type: 'image',
				component_name: 'Front Page',
				thumbnail_url: 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=400'
			},
			{
				component_id: 'img_002',
				component_type: 'image',
				component_name: 'Back Page',
				thumbnail_url: 'https://images.unsplash.com/photo-1589519160732-57fc498494f8?w=400'
			}
		],
		created_at: '2024-01-15T10:30:00Z'
	},
	{
		group_id: '2',
		group_name: 'Passport Documents',
		components: [
			{
				component_id: 'img_003',
				component_type: 'image',
				component_name: 'Main Page',
				thumbnail_url: 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=400'
			},
			{
				component_id: 'img_004',
				component_type: 'image',
				component_name: 'Visa Page',
				thumbnail_url: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400'
			},
			{
				component_id: 'img_005',
				component_type: 'image',
				component_name: 'Stamps Page',
				thumbnail_url: 'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=400'
			}
		],
		created_at: '2024-01-16T14:20:00Z'
	},
	{
		group_id: '3',
		group_name: 'Driver License',
		components: [
			{
				component_id: 'img_006',
				component_type: 'image',
				component_name: 'Front',
				thumbnail_url: 'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=400'
			},
			{
				component_id: 'img_007',
				component_type: 'image',
				component_name: 'Back',
				thumbnail_url: 'https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=400'
			}
		],
		created_at: '2024-01-17T09:15:00Z'
	},
	{
		group_id: '4',
		group_name: 'Medical Records',
		components: [
			{
				component_id: 'img_008',
				component_type: 'image',
				component_name: 'Lab Results',
				thumbnail_url: 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400'
			},
			{
				component_id: 'img_009',
				component_type: 'image',
				component_name: 'Prescription',
				thumbnail_url: 'https://images.unsplash.com/photo-1471864190281-a93a3070b6de?w=400'
			},
			{
				component_id: 'img_010',
				component_type: 'image',
				component_name: 'X-Ray',
				thumbnail_url: 'https://images.unsplash.com/photo-1530026405186-ed1f139313f8?w=400'
			},
			{
				component_id: 'img_011',
				component_type: 'image',
				component_name: 'Insurance Card',
				thumbnail_url: 'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=400'
			}
		],
		created_at: '2024-01-18T11:45:00Z'
	},
	{
		group_id: '5',
		group_name: 'Bank Statements',
		components: [
			{
				component_id: 'img_012',
				component_type: 'image',
				component_name: 'January Statement',
				thumbnail_url: 'https://images.unsplash.com/photo-1554224154-26032ffc0d07?w=400'
			},
			{
				component_id: 'img_013',
				component_type: 'image',
				component_name: 'February Statement',
				thumbnail_url: 'https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=400'
			}
		],
		created_at: '2024-01-19T08:30:00Z'
	},
	{
		group_id: '6',
		group_name: 'Utility Bills',
		components: [
			{
				component_id: 'img_014',
				component_type: 'image',
				component_name: 'Electric Bill',
				thumbnail_url: 'https://images.unsplash.com/photo-1473186578172-c141e6798cf4?w=400'
			},
			{
				component_id: 'img_015',
				component_type: 'image',
				component_name: 'Water Bill',
				thumbnail_url: 'https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=400'
			},
			{
				component_id: 'img_016',
				component_type: 'image',
				component_name: 'Internet Bill',
				thumbnail_url: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400'
			}
		],
		created_at: '2024-01-20T14:20:00Z'
	},
	{
		group_id: '7',
		group_name: 'Receipts',
		components: [
			{
				component_id: 'img_017',
				component_type: 'image',
				component_name: 'Grocery Receipt',
				thumbnail_url: 'https://images.unsplash.com/photo-1534723328310-e82dad3ee43f?w=400'
			},
			{
				component_id: 'img_018',
				component_type: 'image',
				component_name: 'Electronics Purchase',
				thumbnail_url: 'https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=400'
			},
			{
				component_id: 'img_019',
				component_type: 'image',
				component_name: 'Restaurant Bill',
				thumbnail_url: 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400'
			},
			{
				component_id: 'img_020',
				component_type: 'image',
				component_name: 'Gas Station',
				thumbnail_url: 'https://images.unsplash.com/photo-1545262810-77515befe149?w=400'
			},
			{
				component_id: 'img_021',
				component_type: 'image',
				component_name: 'Pharmacy',
				thumbnail_url: 'https://images.unsplash.com/photo-1587854692152-cbe660dbde88?w=400'
			}
		],
		created_at: '2024-01-21T16:10:00Z'
	},
	{
		group_id: '8',
		group_name: 'Business Cards',
		components: [
			{
				component_id: 'img_022',
				component_type: 'image',
				component_name: 'Contact 1',
				thumbnail_url: 'https://images.unsplash.com/photo-1589330694653-ded6df03f754?w=400'
			},
			{
				component_id: 'img_023',
				component_type: 'image',
				component_name: 'Contact 2',
				thumbnail_url: 'https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=400'
			}
		],
		created_at: '2024-01-22T10:00:00Z'
	},
	{
		group_id: '9',
		group_name: 'Invoices',
		components: [
			{
				component_id: 'img_024',
				component_type: 'image',
				component_name: 'Invoice #001',
				thumbnail_url: 'https://images.unsplash.com/photo-1554224154-22dec7ec8818?w=400'
			},
			{
				component_id: 'img_025',
				component_type: 'image',
				component_name: 'Invoice #002',
				thumbnail_url: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400'
			},
			{
				component_id: 'img_026',
				component_type: 'image',
				component_name: 'Invoice #003',
				thumbnail_url: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400'
			}
		],
		created_at: '2024-01-23T13:30:00Z'
	},
	{
		group_id: '10',
		group_name: 'Contracts',
		components: [
			{
				component_id: 'img_027',
				component_type: 'image',
				component_name: 'Employment Contract',
				thumbnail_url: 'https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400'
			},
			{
				component_id: 'img_028',
				component_type: 'image',
				component_name: 'NDA',
				thumbnail_url: 'https://images.unsplash.com/photo-1507925921958-8a62f3d1a50d?w=400'
			},
			{
				component_id: 'img_029',
				component_type: 'image',
				component_name: 'Service Agreement',
				thumbnail_url: 'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=400'
			},
			{
				component_id: 'img_030',
				component_type: 'image',
				component_name: 'Lease Agreement',
				thumbnail_url: 'https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=400'
			}
		],
		created_at: '2024-01-24T09:20:00Z'
	},
	{
		group_id: '11',
		group_name: 'Certificates',
		components: [
			{
				component_id: 'img_031',
				component_type: 'image',
				component_name: 'Birth Certificate',
				thumbnail_url: 'https://images.unsplash.com/photo-1521791136064-7986c2920216?w=400'
			},
			{
				component_id: 'img_032',
				component_type: 'image',
				component_name: 'Diploma',
				thumbnail_url: 'https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=400'
			}
		],
		created_at: '2024-01-25T15:45:00Z'
	},
	{
		group_id: '12',
		group_name: 'Tax Documents',
		components: [
			{
				component_id: 'img_033',
				component_type: 'image',
				component_name: 'W-2 Form',
				thumbnail_url: 'https://images.unsplash.com/photo-1554224311-beee4ece0bf8?w=400'
			},
			{
				component_id: 'img_034',
				component_type: 'image',
				component_name: '1099 Form',
				thumbnail_url: 'https://images.unsplash.com/photo-1568992687947-868a62a9f521?w=400'
			},
			{
				component_id: 'img_035',
				component_type: 'image',
				component_name: 'Tax Return',
				thumbnail_url: 'https://images.unsplash.com/photo-1554224311-beee4ece0bf8?w=400'
			}
		],
		created_at: '2024-01-26T12:00:00Z'
	},
	{
		group_id: '13',
		group_name: 'Insurance Documents',
		components: [
			{
				component_id: 'img_036',
				component_type: 'image',
				component_name: 'Auto Insurance',
				thumbnail_url: 'https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=400'
			},
			{
				component_id: 'img_037',
				component_type: 'image',
				component_name: 'Home Insurance',
				thumbnail_url: 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400'
			},
			{
				component_id: 'img_038',
				component_type: 'image',
				component_name: 'Life Insurance',
				thumbnail_url: 'https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400'
			},
			{
				component_id: 'img_039',
				component_type: 'image',
				component_name: 'Health Insurance',
				thumbnail_url: 'https://images.unsplash.com/photo-1584515933487-779824d29309?w=400'
			}
		],
		created_at: '2024-01-27T10:30:00Z'
	}
];

export const GET: RequestHandler = async ({ url }) => {
	// Simulate network delay
	await new Promise((resolve) => setTimeout(resolve, 300));

	// Support filtering by query params if needed
	const filterName = url.searchParams.get('name');

	let groups = mockGroups;

	if (filterName) {
		groups = mockGroups.filter((g) =>
			g.group_name.toLowerCase().includes(filterName.toLowerCase())
		);
	}

	return json({
		groups,
		total: groups.length
	});
};
