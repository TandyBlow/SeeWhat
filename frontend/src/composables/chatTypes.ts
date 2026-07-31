export interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
  timestamp?: number;
  metadata?: Record<string, unknown>;
}

export interface MentionedConcept {
  name: string;
  category: string;
  definition: string;
  prerequisites: string[];
  expansion_directions: string[];
  verified: boolean;
  wiki_summary: string;
  wiki_description: string;
}

export type ChatMode = 'idle' | 'text_input' | 'file_upload' | 'file_uploaded' | 'conversing' | 'ocr_progress';

export interface ChatCheckpoint {
  sessionId: string;
  nodeId: string;
  mode: string;
  timestamp: number;
}

export interface CheckpointMap {
  [nodeId: string]: ChatCheckpoint;
}
