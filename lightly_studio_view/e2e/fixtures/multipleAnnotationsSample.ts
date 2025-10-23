import { SampleFixture } from './types';

export const multipleAnnotationsSample: SampleFixture = {
    name: '000000001732.jpg',
    annotations: [
        {
            label: 'cell phone',
            coordinates: {
                x: 288,
                y: 144,
                width: 19,
                height: 20
            }
        },
        {
            label: 'person',
            coordinates: {
                x: 209,
                y: 105,
                width: 133,
                height: 300
            }
        },
        {
            label: 'handbag',
            coordinates: {
                x: 199,
                y: 241,
                width: 42,
                height: 74
            }
        }
    ]
};
