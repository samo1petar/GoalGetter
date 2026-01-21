// LLM Provider types
export type LLMProvider = 'claude' | 'openai';

export interface LLMProviderInfo {
  id: LLMProvider;
  name: string;
  description: string;
  available: boolean;
}

export interface AvailableProvidersResponse {
  providers: LLMProviderInfo[];
  current: LLMProvider;
}

// User types
export interface UserSettings {
  meeting_duration: number;
  timezone: string;
  email_notifications: boolean;
}

export interface User {
  id: string;
  email: string;
  name: string;
  auth_provider: 'email' | 'google';
  profile_image: string | null;
  phase: 'goal_setting' | 'tracking';
  meeting_interval: number;
  calendar_connected: boolean;
  two_factor_enabled: boolean;
  llm_provider: LLMProvider;
  created_at: string;
  updated_at: string;
  settings: UserSettings;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface TwoFactorRequiredResponse {
  requires_2fa: boolean;
  message: string;
}

export interface TwoFactorSetupResponse {
  secret: string;
  qr_code_uri: string;
  backup_codes: string[];
}

export type LoginResponse = AuthResponse | TwoFactorRequiredResponse;

// Goal types
export interface Milestone {
  title: string;
  description?: string;
  target_date?: string;
  completed: boolean;
  completed_at?: string;
}

export type ContentFormat = 'markdown' | 'blocknote_json';

export interface GoalMetadata {
  deadline?: string;
  milestones: Milestone[];
  tags: string[];
  content_format?: ContentFormat;
}

export interface Goal {
  id: string;
  user_id: string;
  title: string;
  content: string;
  phase: 'draft' | 'active' | 'completed' | 'archived';
  template_type: 'smart' | 'okr' | 'custom';
  created_at: string;
  updated_at: string;
  metadata: GoalMetadata;
}

export interface GoalListResponse {
  goals: Goal[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateGoalRequest {
  title: string;
  content?: string;
  phase?: 'draft' | 'active' | 'completed' | 'archived';
  template_type?: 'smart' | 'okr' | 'custom';
  deadline?: string;
  milestones?: Milestone[];
  tags?: string[];
}

export interface UpdateGoalRequest {
  title?: string;
  content?: string;
  phase?: 'draft' | 'active' | 'completed' | 'archived';
  deadline?: string;
  milestones?: Milestone[];
  tags?: string[];
}

// Chat types
export interface ChatMessage {
  id: string;
  user_id: string;
  role: 'user' | 'assistant';
  content: string;
  meeting_id?: string;
  timestamp: string;
  metadata?: {
    model?: string;
    tokens_used?: number;
  };
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface ChatAccessResponse {
  can_access: boolean;
  reason: string;
  user_phase: string;
  next_available?: string;
  meeting_id?: string;
}

// Tool call result from AI Coach
export interface ToolCallResult {
  success: boolean;
  goal_id?: string;
  goal?: Goal;
  error?: string;
}

// Draft goal payload sent with chat messages
export interface DraftGoalPayload {
  id?: string;
  title: string;
  content: string;
  template_type: string;
}

export interface WebSocketMessage {
  type: 'connected' | 'typing' | 'response_chunk' | 'response' | 'error' | 'pong' | 'tool_call';
  content?: string;
  message_id?: string;
  is_complete?: boolean;
  error?: string;
  user_phase?: string;
  meeting_id?: string;
  tokens_used?: number;
  // Tool call fields
  tool?: 'create_goal' | 'update_goal' | 'set_goal_phase';
  tool_result?: ToolCallResult;
}

// Chat message with provider selection
export interface ChatMessagePayload {
  type: 'message';
  content: string;
  draft_goals?: DraftGoalPayload[];
  active_goal_id?: string;
  provider?: LLMProvider;
}

// Meeting types
export interface Meeting {
  id: string;
  user_id: string;
  scheduled_at: string;
  duration_minutes: number;
  status: 'scheduled' | 'active' | 'completed' | 'cancelled';
  calendar_event_id?: string;
  notes?: string;
  created_at: string;
  completed_at?: string;
}

export interface MeetingListResponse {
  meetings: Meeting[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface NextMeetingResponse {
  meeting: Meeting | null;
  message: string;
  can_access_now: boolean;
  countdown_seconds: number;
}

// Template types
export interface Template {
  id: string;
  name: string;
  description: string;
  template_type: 'smart' | 'okr' | 'custom';
  structure: Record<string, unknown>;
}

// API Error
export interface ApiError {
  detail: string;
  status_code?: number;
}
