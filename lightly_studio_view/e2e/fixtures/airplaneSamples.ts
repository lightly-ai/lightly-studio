import { SampleFixture } from './types';

export const airplaneSamples: SampleFixture[] = [
    {
        name: '000000262777.jpg',
        annotations: [
            {
                label: 'airplane',
                coordinates: {
                    x: 247,
                    y: 172,
                    width: 33,
                    height: 13
                }
            }
        ]
    },
    {
        name: '000000505447.jpg',
        annotations: [
            {
                label: 'airplane',
                coordinates: {
                    x: 37,
                    y: 91,
                    width: 592,
                    height: 222
                }
            }
        ]
    }
];
