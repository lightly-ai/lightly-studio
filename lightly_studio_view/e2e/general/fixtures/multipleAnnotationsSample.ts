import { SampleFixture } from './types';

export const multipleAnnotationsSample: SampleFixture = {
    name: '000000001732.jpg',
    annotations: [
        {
            label: 'cell phone',
            coordinates: {
                x: 288,
                y: 144,
                width: 20,
                height: 21
            }
        },
        {
            label: 'person',
            coordinates: {
                x: 209,
                y: 105,
                width: 135,
                height: 302
            }
        },
        {
            label: 'handbag',
            coordinates: {
                x: 199,
                y: 241,
                width: 43,
                height: 75
            }
        }
    ]
};
