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
                    width: 130,
                    height: 102
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
                    width: 339,
                    height: 404
                }
            },
            {
                label: 'bear',
                coordinates: {
                    x: 1,
                    y: 0,
                    width: 493,
                    height: 589
                }
            }
        ]
    }
];
