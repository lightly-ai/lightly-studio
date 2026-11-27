import { SampleFixture } from './types';

export const bearSamples: SampleFixture[] = [
    {
        name: '000000467685.jpg',
        annotations: [
            {
                label: 'bear',
                coordinates: {
                    x: 237,
                    y: 194,
                    width: 131,
                    height: 103
                }
            }
        ]
    },
    {
        name: '000000499104.jpg',
        annotations: [
            {
                label: 'bear',
                coordinates: {
                    x: 155,
                    y: 235,
                    width: 340,
                    height: 405
                }
            },
            {
                label: 'bear',
                coordinates: {
                    x: 1,
                    y: 0,
                    width: 494,
                    height: 590
                }
            }
        ]
    }
];
