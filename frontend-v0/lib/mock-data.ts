// Mock data for RevMax prototype

export type Recommendation = 'raise' | 'hold' | 'lower';

export interface Hotel {
  id: string;
  name: string;
  city: string;
  neighborhood: string;
  category: string;
  targetRoomType: string;
  officialWebsite: string;
  clientEmail: string;
  status: 'active' | 'inactive' | 'pending';
  plan: 'starter' | 'professional' | 'enterprise';
  currentStrategy: string;
  lastAnalysis: string;
}

export interface AnalysisResult {
  hotelId: string;
  recommendation: Recommendation;
  confidence: number;
  summary: string;
  yourPrice: number;
  marketAverage: number;
  pricePosition: { rank: number; total: number };
  demandIndex: number;
  demandLevel: 'low' | 'moderate' | 'high' | 'very-high';
  reputation: number;
  visibility: 'low' | 'medium' | 'high';
  marketContext: string;
  events: string[];
  parityStatus: 'ok' | 'warning' | 'violation';
  channelsChecked: string[];
  parityMessage: string;
  compSet: Competitor[];
  actionSummary: string;
  actionBullets: string[];
  qualityLabel: 'excellent' | 'good' | 'degraded' | 'poor';
  fallbackCount: number;
  qualityNote: string;
  lastAnalysisRun: string;
  progress: AnalysisStep[];
}

export interface Competitor {
  id: string;
  name: string;
  type: 'primary' | 'aspirational' | 'surveillance';
  price?: number;
}

export interface AnalysisStep {
  id: number;
  name: string;
  status: 'done' | 'active' | 'warning' | 'error' | 'pending';
  message?: string;
}

export interface Report {
  id: string;
  hotelId: string;
  hotelName: string;
  date: string;
  recommendation: Recommendation;
  confidence: number;
  executiveSummary: string;
  priceComparison: {
    yourPrice: number;
    marketAverage: number;
    position: string;
  };
  marketDemand: string;
  events: string[];
  distributionParity: string;
  suggestedAction: string;
  confidenceLimits: string;
}

export interface Alert {
  id: string;
  hotelId: string;
  hotelName: string;
  type: 'parity_violation' | 'weak_demand' | 'underpricing' | 'visibility_issue' | 'competitor_pressure';
  severity: 'critical' | 'high' | 'medium';
  title: string;
  description: string;
  timestamp: string;
  status: 'new' | 'acknowledged' | 'resolved';
}

export interface TrainingCase {
  id: string;
  hotelId: string;
  hotelName: string;
  currentPrice: number;
  marketAverage: number;
  demandLevel: 'low' | 'moderate' | 'high' | 'very-high';
  recommendation: Recommendation;
  confidence: number;
  reasoning: string;
  userScore?: number;
  userFeedback?: string;
  adjustmentDecision?: string;
}

// Hotels
export const hotels: Hotel[] = [
  {
    id: 'h1',
    name: 'Catalonia Berlin Mitte',
    city: 'Berlin',
    neighborhood: 'Mitte',
    category: '4-star',
    targetRoomType: 'Standard Double',
    officialWebsite: 'https://www.cataloniahotels.com/en/hotel/catalonia-berlin-mitte',
    clientEmail: 'revenue@catalonia-berlin.com',
    status: 'active',
    plan: 'professional',
    currentStrategy: 'Dynamic Pricing',
    lastAnalysis: '2 minutes ago'
  },
  {
    id: 'h2',
    name: 'Hotel Arts Barcelona',
    city: 'Barcelona',
    neighborhood: 'Vila Olímpica',
    category: '5-star Luxury',
    targetRoomType: 'Deluxe Sea View',
    officialWebsite: 'https://www.hotelartsbarcelona.com',
    clientEmail: 'revenue@hotelartsbarcelona.com',
    status: 'active',
    plan: 'enterprise',
    currentStrategy: 'Premium Positioning',
    lastAnalysis: '15 minutes ago'
  },
  {
    id: 'h3',
    name: 'NH Collection Berlin Mitte',
    city: 'Berlin',
    neighborhood: 'Friedrichstraße',
    category: '4-star Superior',
    targetRoomType: 'Superior Room',
    officialWebsite: 'https://www.nh-hotels.com/hotel/nh-collection-berlin-mitte',
    clientEmail: 'rm.berlin@nh-hotels.com',
    status: 'active',
    plan: 'professional',
    currentStrategy: 'Competitive Matching',
    lastAnalysis: '1 hour ago'
  },
  {
    id: 'h4',
    name: 'Hampton by Hilton Berlin',
    city: 'Berlin',
    neighborhood: 'City East',
    category: '3-star',
    targetRoomType: 'Queen Room',
    officialWebsite: 'https://www.hilton.com/en/hotels/berhxhx-hampton-berlin-city-east',
    clientEmail: 'revenue@hampton-berlin.com',
    status: 'active',
    plan: 'starter',
    currentStrategy: 'Value Leader',
    lastAnalysis: '3 hours ago'
  },
  {
    id: 'h5',
    name: 'Park Inn Alexanderplatz',
    city: 'Berlin',
    neighborhood: 'Alexanderplatz',
    category: '4-star',
    targetRoomType: 'Standard Room',
    officialWebsite: 'https://www.parkinn.com/hotel-berlin',
    clientEmail: 'parkinn.berlin@rezidor.com',
    status: 'pending',
    plan: 'professional',
    currentStrategy: 'Under Review',
    lastAnalysis: 'Pending'
  }
];

// Analysis Results
export const analysisResults: Record<string, AnalysisResult> = {
  h1: {
    hotelId: 'h1',
    recommendation: 'raise',
    confidence: 78,
    summary: 'Your current price is below the comparable market during a period of strong local demand. Consider increasing rates to capture additional revenue.',
    yourPrice: 89,
    marketAverage: 112,
    pricePosition: { rank: 3, total: 12 },
    demandIndex: 74,
    demandLevel: 'high',
    reputation: 8.3,
    visibility: 'medium',
    marketContext: 'Demand is currently elevated in your area and several comparable hotels are selling above your current rate. Your price appears slightly aggressive for the current market context. The upcoming ITB Berlin trade show is driving significant booking activity.',
    events: ['ITB Berlin', 'Messe Conference Week', 'Berlin Marathon Week'],
    parityStatus: 'ok',
    channelsChecked: ['Booking.com', 'Expedia', 'Hotels.com', 'Google Hotels', 'Official Website'],
    parityMessage: 'No relevant discrepancies detected across major channels.',
    compSet: [
      { id: 'c1', name: 'NH Collection Berlin Mitte', type: 'primary', price: 119 },
      { id: 'c2', name: 'Adina Apartment Hotel Berlin Mitte', type: 'primary', price: 105 },
      { id: 'c3', name: 'Meliá Berlin', type: 'aspirational', price: 142 },
      { id: 'c4', name: 'Hampton by Hilton Berlin', type: 'surveillance', price: 79 }
    ],
    actionSummary: 'Your current price suggests an aggressive demand-capture strategy. That works well when demand is weak. However, current demand in your area appears strong and several comparable hotels are selling at higher rates.',
    actionBullets: [
      'Increase price by 15–20% to €102–107',
      'Monitor conversion over the next 24–48h',
      'Recheck compset tomorrow morning'
    ],
    qualityLabel: 'excellent',
    fallbackCount: 0,
    qualityNote: 'All data sources responded successfully. High confidence in market assessment.',
    lastAnalysisRun: '2 minutes ago',
    progress: [
      { id: 1, name: 'Identifying hotel', status: 'done' },
      { id: 2, name: 'Detecting comparable hotels', status: 'done' },
      { id: 3, name: 'Checking prices and availability', status: 'done' },
      { id: 4, name: 'Analyzing demand', status: 'done' },
      { id: 5, name: 'Analyzing reputation', status: 'done' },
      { id: 6, name: 'Reviewing distribution and parity', status: 'done' },
      { id: 7, name: 'Calculating strategy and opportunities', status: 'done' },
      { id: 8, name: 'Prioritizing actions and scenarios', status: 'done' },
      { id: 9, name: 'Generating report', status: 'done' }
    ]
  },
  h2: {
    hotelId: 'h2',
    recommendation: 'hold',
    confidence: 62,
    summary: 'Your current rate is well-positioned within the luxury segment. Market conditions are stable and your pricing reflects appropriate value.',
    yourPrice: 385,
    marketAverage: 372,
    pricePosition: { rank: 4, total: 8 },
    demandIndex: 58,
    demandLevel: 'moderate',
    reputation: 9.1,
    visibility: 'high',
    marketContext: 'The luxury segment in Barcelona is experiencing stable demand. Your premium positioning is justified by your superior reputation score and beachfront location. No significant events are driving unusual demand patterns.',
    events: [],
    parityStatus: 'ok',
    channelsChecked: ['Booking.com', 'Expedia', 'Hotels.com', 'Google Hotels', 'Official Website', 'Luxury Escapes'],
    parityMessage: 'Rate parity maintained across all distribution channels.',
    compSet: [
      { id: 'c5', name: 'W Barcelona', type: 'primary', price: 395 },
      { id: 'c6', name: 'Mandarin Oriental Barcelona', type: 'aspirational', price: 520 },
      { id: 'c7', name: 'Hotel Miramar Barcelona', type: 'primary', price: 345 }
    ],
    actionSummary: 'Your current pricing strategy is appropriate for market conditions. The slight premium over market average is justified by your reputation advantage.',
    actionBullets: [
      'Maintain current rate structure',
      'Monitor upcoming events calendar',
      'Review position if demand index changes significantly'
    ],
    qualityLabel: 'good',
    fallbackCount: 1,
    qualityNote: '1 agent relied on fallback data. Compset detection is complete.',
    lastAnalysisRun: '15 minutes ago',
    progress: [
      { id: 1, name: 'Identifying hotel', status: 'done' },
      { id: 2, name: 'Detecting comparable hotels', status: 'done' },
      { id: 3, name: 'Checking prices and availability', status: 'done' },
      { id: 4, name: 'Analyzing demand', status: 'done' },
      { id: 5, name: 'Analyzing reputation', status: 'done' },
      { id: 6, name: 'Reviewing distribution and parity', status: 'done' },
      { id: 7, name: 'Calculating strategy and opportunities', status: 'done' },
      { id: 8, name: 'Prioritizing actions and scenarios', status: 'done' },
      { id: 9, name: 'Generating report', status: 'done' }
    ]
  },
  h3: {
    hotelId: 'h3',
    recommendation: 'lower',
    confidence: 71,
    summary: 'Your current price is above market average during a period of softening demand. Consider a tactical reduction to improve conversion.',
    yourPrice: 134,
    marketAverage: 112,
    pricePosition: { rank: 10, total: 12 },
    demandIndex: 42,
    demandLevel: 'low',
    reputation: 8.1,
    visibility: 'medium',
    marketContext: 'Demand in the Friedrichstraße area has softened following the end of fashion week. Competitors are adjusting rates downward and your price position has become less competitive. Booking pace has slowed significantly.',
    events: [],
    parityStatus: 'warning',
    channelsChecked: ['Booking.com', 'Expedia', 'Hotels.com', 'Google Hotels', 'Official Website'],
    parityMessage: 'Minor rate discrepancy detected on Expedia (€129 vs €134 official).',
    compSet: [
      { id: 'c8', name: 'Catalonia Berlin Mitte', type: 'primary', price: 89 },
      { id: 'c9', name: 'Radisson Blu Berlin', type: 'primary', price: 125 },
      { id: 'c10', name: 'The Regent Berlin', type: 'aspirational', price: 245 }
    ],
    actionSummary: 'Market conditions have shifted and your current rate is creating friction. A tactical price adjustment will help maintain booking velocity.',
    actionBullets: [
      'Reduce price by 10–15% to €114–121',
      'Resolve Expedia parity issue',
      'Consider promotional package to drive direct bookings'
    ],
    qualityLabel: 'good',
    fallbackCount: 1,
    qualityNote: '1 agent relied on fallback data for demand forecast.',
    lastAnalysisRun: '1 hour ago',
    progress: [
      { id: 1, name: 'Identifying hotel', status: 'done' },
      { id: 2, name: 'Detecting comparable hotels', status: 'done' },
      { id: 3, name: 'Checking prices and availability', status: 'done' },
      { id: 4, name: 'Analyzing demand', status: 'done' },
      { id: 5, name: 'Analyzing reputation', status: 'warning', message: 'Limited review data available' },
      { id: 6, name: 'Reviewing distribution and parity', status: 'done' },
      { id: 7, name: 'Calculating strategy and opportunities', status: 'done' },
      { id: 8, name: 'Prioritizing actions and scenarios', status: 'done' },
      { id: 9, name: 'Generating report', status: 'done' }
    ]
  },
  h4: {
    hotelId: 'h4',
    recommendation: 'hold',
    confidence: 85,
    summary: 'Your value positioning is working effectively. Current rate optimizes occupancy while maintaining healthy RevPAR.',
    yourPrice: 79,
    marketAverage: 112,
    pricePosition: { rank: 1, total: 12 },
    demandIndex: 68,
    demandLevel: 'moderate',
    reputation: 7.8,
    visibility: 'high',
    marketContext: 'As the value leader in the market, you are capturing price-sensitive demand effectively. Your occupancy rates are strong and review scores are improving.',
    events: ['Berlin Light Festival'],
    parityStatus: 'ok',
    channelsChecked: ['Booking.com', 'Expedia', 'Hotels.com', 'Google Hotels', 'Official Website'],
    parityMessage: 'All channels in sync.',
    compSet: [
      { id: 'c11', name: 'Motel One Berlin', type: 'primary', price: 75 },
      { id: 'c12', name: 'Holiday Inn Express Berlin', type: 'primary', price: 82 }
    ],
    actionSummary: 'Your current strategy is well-calibrated for your market segment. Continue monitoring competitor movements.',
    actionBullets: [
      'Maintain current rates',
      'Focus on review score improvement',
      'Consider slight increase during Light Festival peak'
    ],
    qualityLabel: 'excellent',
    fallbackCount: 0,
    qualityNote: 'All data sources responded successfully.',
    lastAnalysisRun: '3 hours ago',
    progress: [
      { id: 1, name: 'Identifying hotel', status: 'done' },
      { id: 2, name: 'Detecting comparable hotels', status: 'done' },
      { id: 3, name: 'Checking prices and availability', status: 'done' },
      { id: 4, name: 'Analyzing demand', status: 'done' },
      { id: 5, name: 'Analyzing reputation', status: 'done' },
      { id: 6, name: 'Reviewing distribution and parity', status: 'done' },
      { id: 7, name: 'Calculating strategy and opportunities', status: 'done' },
      { id: 8, name: 'Prioritizing actions and scenarios', status: 'done' },
      { id: 9, name: 'Generating report', status: 'done' }
    ]
  }
};

// Reports
export const reports: Report[] = [
  {
    id: 'r1',
    hotelId: 'h1',
    hotelName: 'Catalonia Berlin Mitte',
    date: '2024-03-15',
    recommendation: 'raise',
    confidence: 78,
    executiveSummary: 'Strong demand signals and favorable market conditions support a price increase of 15–20%. Competitors are pricing higher and ITB Berlin is driving additional demand.',
    priceComparison: { yourPrice: 89, marketAverage: 112, position: '#3 of 12' },
    marketDemand: 'High demand driven by ITB Berlin trade show and conference activity.',
    events: ['ITB Berlin', 'Messe Conference Week'],
    distributionParity: 'All channels in sync. No rate violations detected.',
    suggestedAction: 'Increase rates to €102–107 and monitor conversion.',
    confidenceLimits: 'High confidence analysis with all data sources responding.'
  },
  {
    id: 'r2',
    hotelId: 'h2',
    hotelName: 'Hotel Arts Barcelona',
    date: '2024-03-15',
    recommendation: 'hold',
    confidence: 62,
    executiveSummary: 'Market conditions are stable and current pricing is appropriate for the luxury segment. Maintain current strategy.',
    priceComparison: { yourPrice: 385, marketAverage: 372, position: '#4 of 8' },
    marketDemand: 'Moderate demand with stable booking patterns.',
    events: [],
    distributionParity: 'Rate parity maintained across all channels.',
    suggestedAction: 'Maintain current rate structure and monitor events calendar.',
    confidenceLimits: 'Good confidence with minor data limitations.'
  },
  {
    id: 'r3',
    hotelId: 'h3',
    hotelName: 'NH Collection Berlin Mitte',
    date: '2024-03-14',
    recommendation: 'lower',
    confidence: 71,
    executiveSummary: 'Softening demand and competitive pressure suggest a tactical price reduction would improve conversion rates.',
    priceComparison: { yourPrice: 134, marketAverage: 112, position: '#10 of 12' },
    marketDemand: 'Low demand following fashion week conclusion.',
    events: [],
    distributionParity: 'Minor Expedia parity issue requires attention.',
    suggestedAction: 'Reduce rates by 10–15% and resolve parity discrepancy.',
    confidenceLimits: 'Good confidence with fallback data on demand forecast.'
  },
  {
    id: 'r4',
    hotelId: 'h1',
    hotelName: 'Catalonia Berlin Mitte',
    date: '2024-03-10',
    recommendation: 'hold',
    confidence: 65,
    executiveSummary: 'Market conditions stable. Current pricing appropriate for demand levels.',
    priceComparison: { yourPrice: 85, marketAverage: 92, position: '#4 of 12' },
    marketDemand: 'Moderate demand with no significant events.',
    events: [],
    distributionParity: 'All channels in sync.',
    suggestedAction: 'Maintain current rates.',
    confidenceLimits: 'Standard analysis quality.'
  },
  {
    id: 'r5',
    hotelId: 'h4',
    hotelName: 'Hampton by Hilton Berlin',
    date: '2024-03-12',
    recommendation: 'hold',
    confidence: 85,
    executiveSummary: 'Value positioning is effective. Occupancy strong and RevPAR healthy.',
    priceComparison: { yourPrice: 79, marketAverage: 112, position: '#1 of 12' },
    marketDemand: 'Moderate demand with Light Festival approaching.',
    events: ['Berlin Light Festival'],
    distributionParity: 'All channels aligned.',
    suggestedAction: 'Maintain rates with potential increase during festival peak.',
    confidenceLimits: 'Excellent data quality.'
  }
];

// Alerts
export const alerts: Alert[] = [
  {
    id: 'a1',
    hotelId: 'h3',
    hotelName: 'NH Collection Berlin Mitte',
    type: 'parity_violation',
    severity: 'critical',
    title: 'Rate Parity Violation',
    description: 'Expedia showing €129 vs €134 official rate. 3.7% discrepancy detected.',
    timestamp: '2024-03-15T10:30:00',
    status: 'new'
  },
  {
    id: 'a2',
    hotelId: 'h1',
    hotelName: 'Catalonia Berlin Mitte',
    type: 'underpricing',
    severity: 'high',
    title: 'Significant Underpricing Detected',
    description: 'Current rate €89 is 20% below market average €112 during high demand period.',
    timestamp: '2024-03-15T09:15:00',
    status: 'new'
  },
  {
    id: 'a3',
    hotelId: 'h3',
    hotelName: 'NH Collection Berlin Mitte',
    type: 'weak_demand',
    severity: 'high',
    title: 'Demand Softening',
    description: 'Demand index dropped from 58 to 42 over past 7 days. Booking pace slowing.',
    timestamp: '2024-03-15T08:00:00',
    status: 'acknowledged'
  },
  {
    id: 'a4',
    hotelId: 'h5',
    hotelName: 'Park Inn Alexanderplatz',
    type: 'visibility_issue',
    severity: 'medium',
    title: 'Visibility Score Declining',
    description: 'Search ranking dropped on Booking.com. Review response rate below threshold.',
    timestamp: '2024-03-14T16:45:00',
    status: 'acknowledged'
  },
  {
    id: 'a5',
    hotelId: 'h2',
    hotelName: 'Hotel Arts Barcelona',
    type: 'competitor_pressure',
    severity: 'medium',
    title: 'Competitor Price Movement',
    description: 'W Barcelona reduced rates by 8%. Monitor for impact on booking share.',
    timestamp: '2024-03-14T14:20:00',
    status: 'resolved'
  }
];

// Training Cases
export const trainingCases: TrainingCase[] = [
  {
    id: 'tc1',
    hotelId: 'h1',
    hotelName: 'Catalonia Berlin Mitte',
    currentPrice: 89,
    marketAverage: 112,
    demandLevel: 'high',
    recommendation: 'raise',
    confidence: 78,
    reasoning: 'Strong demand indicators and 20% price gap to market average during ITB Berlin suggest significant revenue opportunity. Compset analysis shows room for 15–20% increase.'
  },
  {
    id: 'tc2',
    hotelId: 'h3',
    hotelName: 'NH Collection Berlin Mitte',
    currentPrice: 134,
    marketAverage: 112,
    demandLevel: 'low',
    recommendation: 'lower',
    confidence: 71,
    reasoning: 'Demand has softened post-fashion week and price position (#10/12) is creating conversion friction. Tactical reduction recommended to maintain booking velocity.'
  },
  {
    id: 'tc3',
    hotelId: 'h2',
    hotelName: 'Hotel Arts Barcelona',
    currentPrice: 385,
    marketAverage: 372,
    demandLevel: 'moderate',
    recommendation: 'hold',
    confidence: 62,
    reasoning: 'Premium positioning justified by 9.1 reputation score and beachfront location. Slight premium over market is appropriate for luxury segment.'
  },
  {
    id: 'tc4',
    hotelId: 'h4',
    hotelName: 'Hampton by Hilton Berlin',
    currentPrice: 79,
    marketAverage: 112,
    demandLevel: 'moderate',
    recommendation: 'hold',
    confidence: 85,
    reasoning: 'Value leader strategy is working effectively. Strong occupancy and healthy RevPAR. Price position #1 is intentional competitive advantage.'
  },
  {
    id: 'tc5',
    hotelId: 'h1',
    hotelName: 'Catalonia Berlin Mitte',
    currentPrice: 95,
    marketAverage: 98,
    demandLevel: 'moderate',
    recommendation: 'hold',
    confidence: 55,
    reasoning: 'Edge case: Price close to market average, moderate demand, mixed signals from compset. Lower confidence due to ambiguous market conditions.'
  }
];

// System status
export const systemStatus = {
  status: 'operational',
  lastSync: '2 minutes ago',
  analysesToday: 47,
  avgConfidence: 72,
  alertsActive: 4,
  opportunitiesFound: 12
};

// Dashboard metrics
export const dashboardMetrics = {
  analysesToday: 47,
  avgConfidence: 72,
  revenueAlerts: 4,
  opportunitiesFound: 12,
  hotelsNeedingAttention: 2
};

// Latest signals
export const latestSignals = [
  { id: 's1', message: 'ITB Berlin driving 23% demand increase in Mitte district', timestamp: '10 min ago', type: 'demand' },
  { id: 's2', message: 'W Barcelona reduced rates by 8%', timestamp: '2 hours ago', type: 'competitor' },
  { id: 's3', message: 'Expedia parity violation detected for NH Collection', timestamp: '3 hours ago', type: 'parity' },
  { id: 's4', message: 'Berlin Light Festival bookings trending up', timestamp: '5 hours ago', type: 'demand' },
  { id: 's5', message: 'Fashion week concluded - demand normalizing', timestamp: '1 day ago', type: 'event' }
];

// Adjustment decision options
export const adjustmentDecisions = [
  { value: 'adjust_thresholds', label: 'Adjust Thresholds' },
  { value: 'adjust_weights', label: 'Adjust Weights' },
  { value: 'review_prompt_structure', label: 'Review Prompt Structure' },
  { value: 'review_action_rules', label: 'Review Action Rules' },
  { value: 'review_strategy_rules', label: 'Review Strategy Rules' },
  { value: 'no_change_needed', label: 'No Change Needed' }
];

// Progress status messages
export const statusMessages = [
  'Analyzing market prices...',
  'Detecting competitors...',
  'Reviewing distribution channels...',
  'Calculating strategy...',
  'Generating final report...',
  'Evaluating demand patterns...',
  'Processing reputation data...',
  'Checking rate parity...'
];
