declare const process: { env: Record<string, string | undefined> };
declare module 'node:assert' { export const strict: { equal(actual: unknown, expected: unknown): void } }
