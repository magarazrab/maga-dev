export type Plan = 'free' | 'pro' | 'ultra';
export type TrackKind = 'video' | 'audio' | 'text' | 'overlay' | 'effect';
export type MediaKind = 'video' | 'photo' | 'audio' | 'gif';
export interface Keyframe<T = number> { id: string; timeMs: number; value: T; easing: 'linear' | 'easeInOut'; }
export interface Clip { id: string; trackId: string; kind: MediaKind | 'text' | 'effect'; uri?: string; startMs: number; durationMs: number; sourceInMs: number; speed: number; volume: number; opacity: number; rotation: number; scale: number; x: number; y: number; filter?: string; effect?: string; text?: string; keyframes: Record<string, Keyframe[]>; }
export interface Track { id: string; kind: TrackKind; name: string; clips: Clip[]; muted?: boolean; locked?: boolean; }
export interface Project { id: string; userId: string; name: string; fps: 24 | 30 | 60; width: number; height: number; tracks: Track[]; updatedAt: string; }
export interface ExportSettings { resolution: '480p' | '720p' | '1080p' | '2k' | '4k'; fps: 24 | 30 | 60; quality: 'low' | 'medium' | 'high' | 'maximum'; format: 'mp4'; }
