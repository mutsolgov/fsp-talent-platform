/**
 * Domain types & interfaces for FSP IT-Talent Platform
 * Matched with OpenAPI 3.1 & docs/05
 */

export type UserRole = 'candidate' | 'employer' | 'admin' | 'public';

export interface User {
  id: number;
  email: string;
  role: UserRole;
  fullName?: string;
  isPdnConsentGiven: boolean;
  isProfilePublicationConsentGiven: boolean;
}

export type Specialization = 'backend' | 'frontend' | 'ml_data' | 'devops' | 'qa' | 'infosec';
export type Grade = 'junior' | 'middle' | 'senior' | 'lead';
export type SportRank = '3Ю' | '2Ю' | '1Ю' | '3Р' | '2Р' | '1Р' | 'КМС' | 'МС' | 'МСМК' | 'ЗМС';

export interface FspAchievement {
  title: string;
  year: number;
  rank: string;
  stage?: string;
  medal?: 'gold' | 'silver' | 'bronze' | 'participant';
  points?: number;
}

export interface CandidateAnonymizedSummary {
  id: number;
  maskedCode: string; // e.g. "CAND-01" or "RF-77-9021"
  specialization: Specialization;
  verifiedGrade: Grade;
  finalScore: number; // 0..100
  initialScore?: number;
  isPinned?: boolean;
  fspId: string | null;
  sportRank: SportRank | null;
  isFspVerified: boolean;
  theta: number; // KITE IRT theta 0..100
  freshnessScore: number;
  skills: string[];
  matchedSkills?: string[];
  missingSkills?: string[];
  weights?: {
    isFspProfile: boolean;
    wTest: number;
    wStack: number;
    wFsp: number;
    wFreshness: number;
  };
  factors?: {
    testScore: number;
    stackMatchPct: number;
    fspScore: number;
    freshnessScore: number;
  };
  fspAchievements?: FspAchievement[];
  deltaScore?: number;
}

export interface CandidateFullProfileResponse extends CandidateAnonymizedSummary {
  fullName: string;
  email: string;
  phone?: string;
  telegram?: string;
  githubUrl?: string;
  pdfResumeUrl?: string;
  isMasked: boolean;
  cooldownUntil: string | null;
  experienceYears?: number;
  summaryBio?: string;
}

export interface AssessmentTaskItemResponse {
  id: string;
  sessionTaskId: number;
  index: number; // 1..12
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  language: string;
  starterCode: string;
  sampleInput: string;
  sampleOutput: string;
  timeLimitSec: number;
}

export interface AssessmentSessionResponse {
  id: number;
  candidateId: number;
  specialization: Specialization;
  claimedGrade: Grade;
  status: 'in_progress' | 'completed' | 'expired';
  currentTaskIndex: number;
  totalTasks: number;
  timeRemainingSeconds: number;
  startedAt: string;
  expiresAt: string;
}

export interface AssessmentResultsResponse {
  sessionId: number;
  theta: number; // 0..100
  confirmedGrade: Grade;
  isHonors: boolean; // theta >= 88.0
  isPassed: boolean; // theta >= 70.0
  retestLowerOffered: boolean;
  boostTestOffered: boolean;
  breakdown: {
    algorithmicAccuracy: number;
    edgeCaseHandling: number;
    executionSpeed: number;
  };
}

export interface EmployerNeedSummary {
  id: number;
  title: string;
  specialization: Specialization;
  targetGrade: Grade;
  salaryMinRub: number;
  salaryMaxRub: number;
  status: 'active' | 'closed';
  matchedCandidatesCount: number;
  createdAt: string;
}

export interface EmployerNeedDetail extends EmployerNeedSummary {
  requiredSkills: string[];
  optionalSkills: string[];
  description: string;
  teamContext: string;
}

export interface VacancySummary {
  id: number;
  title: string;
  companyName: string;
  inn: string;
  specialization: Specialization;
  grade: Grade;
  salaryMinRub: number;
  salaryMaxRub: number;
  location: string;
  isTrustEmployer: boolean;
  tags: string[];
  createdAt: string;
}

export interface VacancyDetail extends VacancySummary {
  description: string;
  responsibilities: string[];
  requirements: string[];
  benefits: string[];
}

export interface InvitationResponse {
  id: number;
  vacancyId: number;
  vacancyTitle: string;
  employerName: string;
  candidateId: number;
  candidateMaskedCode: string;
  salaryMinRub: number;
  salaryMaxRub: number;
  pitchMessage: string;
  status: 'sent' | 'viewed' | 'accepted' | 'declined' | 'cancelled';
  createdAt: string;
  respondedAt?: string;
}

export interface SavedShortlistSummary {
  id: number;
  needId: number;
  title: string;
  candidateCount: number;
  pinnedCount: number;
  updatedAt: string;
}

export interface SavedShortlistDetailResponse {
  id: number;
  needId: number;
  title: string;
  candidates: CandidateAnonymizedSummary[];
  pinnedIds: number[];
  filterCriteria: Record<string, unknown>;
}

export interface AtsIntegrationConfigResponse {
  provider: 'huntflow' | 'e-staff' | 'potok' | 'custom_webhook';
  webhookUrl: string;
  secretKey: string;
  isEnabled: boolean;
  status: 'healthy' | 'degraded' | 'failing';
  lastPingMs?: number;
  dlqCount: number;
}

export interface AtsWebhookLogEntry {
  id: string;
  eventType: 'invitation.accepted' | 'application.created' | 'ping';
  statusCode: number;
  attempt: number;
  timestamp: string;
  payloadSnippet: string;
  status: 'delivered' | 'retry_scheduled' | 'failed';
}

export interface MicroChallengeDetailResponse {
  id: number;
  title: string;
  specialization: Specialization;
  difficulty: 'junior' | 'middle' | 'senior';
  points: number;
  description: string;
  starterCode: string;
  testCases: Array<{ input: string; expectedOutput: string; isHidden?: boolean }>;
}

export interface BenchmarkReportResponse {
  totalPairs: number;
  ndcgAt5: number;
  ndcgAt10: number;
  precisionAt5: number;
  pearsonR: number;
  itemDiscriminationD: number;
  leakResistance: number;
  status: 'ready' | 'running';
  metrics: Array<{
    name: string;
    value: number;
    threshold: number;
    passed: boolean;
    description: string;
  }>;
}

export interface AuditLogEntry {
  id: number;
  userId: number | null;
  action: string;
  resource: string;
  ipAddress: string;
  userAgent: string;
  timestamp: string;
  isSuspicious: boolean;
  metadata?: Record<string, unknown>;
}

export interface SearchFilters {
  specialization?: Specialization | 'all';
  grade?: Grade | 'all';
  minScore?: number;
  onlyFsp?: boolean;
  skills?: string[];
  region?: string;
  searchQuery?: string;
}
