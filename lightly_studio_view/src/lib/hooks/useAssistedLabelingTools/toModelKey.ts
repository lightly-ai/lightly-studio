// A browser model and a server model can share an id, so a selection names where it runs too.
export const toModelKey = (model: { id: string; runsIn: 'browser' | 'server' }): string =>
    `${model.runsIn}:${model.id}`;
