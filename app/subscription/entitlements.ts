import type { Plan } from '../types/editor';
export const PRODUCTS = { PRO_MONTHLY: '$1.99/month', PRO_YEARLY: '$99/year', ULTRA_MONTHLY: '$4.99/month', ULTRA_YEARLY: '$199/year' } as const;
const order: Record<Plan, number> = { free: 0, pro: 1, ultra: 2 };
export const FEATURE_MIN_PLAN = { export720p: 'free', export1080p: 'pro', export2k: 'ultra', export4k: 'ultra', keyframes: 'pro', chromaKey: 'pro', masks: 'pro', overlays: 'pro', advancedAudio: 'pro', curves: 'ultra', lut: 'ultra', aiCaptions: 'ultra', backgroundRemoval: 'ultra' } as const;
export type Feature = keyof typeof FEATURE_MIN_PLAN;
export function canUse(plan: Plan, feature: Feature): boolean { return order[plan] >= order[FEATURE_MIN_PLAN[feature]]; }
export function planFromRevenueCat(entitlements: { active: Record<string, unknown> }): Plan { if (entitlements.active.ultra) return 'ultra'; if (entitlements.active.pro) return 'pro'; return 'free'; }
