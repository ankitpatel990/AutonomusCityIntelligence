/**
 * Challan & Violation Types (FRD-09)
 * 
 * TypeScript interfaces for the auto-challan and violation enforcement system.
 */

// ============================================
// Violation Types
// ============================================

export type ViolationType = 'RED_LIGHT' | 'SPEEDING' | 'WRONG_DIRECTION' | 'WRONG_LANE' | 'NO_STOPPING';

export type ViolationSeverity = 'LOW' | 'MEDIUM' | 'HIGH';

export interface ViolationEvidence {
  speed?: number;
  speedLimit?: number;
  signalState?: string;
  direction?: string;
  junctionId?: string;
  junctionName?: string;
  excess?: number;
  severity?: string;
}

export interface Violation {
  violationId: string;
  vehicleId: string;
  numberPlate: string;
  type: ViolationType;
  severity: ViolationSeverity;
  location: [number, number];
  junctionId?: string;
  roadId?: string;
  locationName?: string;
  lat?: number;
  lon?: number;
  timestamp: number;
  fineAmount: number;
  evidence: ViolationEvidence;
  processed?: boolean;
  challanId?: string;
}

export interface ViolationStats {
  totalViolations: number;
  violationsByType: Record<ViolationType, number>;
  recentCount: number;
}


// ============================================
// Challan Types
// ============================================

export type ChallanStatus = 'ISSUED' | 'PAID' | 'PENDING' | 'CANCELLED';

export interface Challan {
  challanId: string;
  violationId: string;
  vehicleId: string;
  numberPlate: string;
  ownerName: string;
  violationType: ViolationType;
  violationDescription?: string;
  fineAmount: number;
  status: ChallanStatus;
  location: string;
  locationName?: string;
  lat?: number;
  lon?: number;
  issuedAt: number;
  paidAt?: number;
  transactionId?: string;
}

export interface ChallanStats {
  totalChallans: number;
  totalRevenue: number;
  pendingRevenue: number;
  paidCount: number;
  pendingCount: number;
  paymentRate: number;
  byViolationType: Record<string, number>;
  revenueByType: Record<string, number>;
}


// ============================================
// Vehicle Owner Types
// ============================================

export interface VehicleOwner {
  numberPlate: string;
  ownerName: string;
  contact: string;
  email?: string;
  address?: string;
  walletBalance: number;
  totalChallans: number;
  totalFinesPaid: number;
}

export interface OwnerStats {
  totalOwners: number;
  totalBalance: number;
  totalFinesPaid: number;
  totalChallans: number;
  avgBalance: number;
}


// ============================================
// Transaction Types
// ============================================

export type TransactionStatus = 'SUCCESS' | 'FAILED' | 'PENDING';

export interface ChallanTransaction {
  transactionId: string;
  challanId: string;
  numberPlate: string;
  amount: number;
  previousBalance: number;
  newBalance: number;
  timestamp: number;
  status: TransactionStatus;
  failureReason?: string;
}


// ============================================
// Service Stats Types
// ============================================

export interface AutoChallanServiceStats {
  running: boolean;
  processingInterval: number;
  autoPaymentEnabled: boolean;
  totalProcessed: number;
  totalPaid: number;
  totalFailed: number;
  pendingViolations: number;
  violationStats: ViolationStats;
  challanStats: ChallanStats;
}


// ============================================
// Revenue Types
// ============================================

export interface RevenueStats {
  totalRevenue: number;
  revenueToday: number;
  revenuePending: number;
  revenueByType: Record<string, number>;
  revenueTimeseries: Array<{
    timestamp: number;
    amount: number;
  }>;
}


// ============================================
// API Response Types
// ============================================

export interface ViolationsResponse {
  violations: Violation[];
  stats: ViolationStats;
}

export interface ChallansResponse {
  challans: Challan[];
  stats: ChallanStats;
}

export interface ServiceStatsResponse {
  status: 'running' | 'stopped' | 'not_initialized';
  message?: string;
  stats?: AutoChallanServiceStats;
}


// ============================================
// API Client
// ============================================

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const challanAPI = {
  // Violations
  getViolations: async (limit: number = 50): Promise<Violation[]> => {
    const res = await fetch(`${API_BASE}/api/violations?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch violations');
    return res.json();
  },
  
  getRecentViolations: async (limit: number = 20): Promise<Violation[]> => {
    const res = await fetch(`${API_BASE}/api/violations/recent?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch recent violations');
    return res.json();
  },
  
  getLiveViolations: async (): Promise<ViolationsResponse> => {
    const res = await fetch(`${API_BASE}/api/challan/violations/live`);
    if (!res.ok) throw new Error('Failed to fetch live violations');
    return res.json();
  },
  
  // Challans
  getChallans: async (status?: ChallanStatus, limit: number = 50): Promise<Challan[]> => {
    let url = `${API_BASE}/api/challans?limit=${limit}`;
    if (status) url += `&status=${status}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch challans');
    return res.json();
  },
  
  getChallan: async (challanId: string): Promise<Challan> => {
    const res = await fetch(`${API_BASE}/api/challans/${challanId}`);
    if (!res.ok) throw new Error('Failed to fetch challan');
    return res.json();
  },
  
  getChallanStats: async (): Promise<ChallanStats> => {
    const res = await fetch(`${API_BASE}/api/challans/stats`);
    if (!res.ok) throw new Error('Failed to fetch challan stats');
    return res.json();
  },
  
  getLiveChallans: async (): Promise<ChallansResponse> => {
    const res = await fetch(`${API_BASE}/api/challan/challans/live`);
    if (!res.ok) throw new Error('Failed to fetch live challans');
    return res.json();
  },
  
  payChallan: async (challanId: string): Promise<ChallanTransaction> => {
    const res = await fetch(`${API_BASE}/api/challans/pay/${challanId}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to pay challan');
    return res.json();
  },
  
  // Owners
  getOwners: async (limit: number = 50): Promise<VehicleOwner[]> => {
    const res = await fetch(`${API_BASE}/api/owners?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch owners');
    return res.json();
  },
  
  getOwner: async (numberPlate: string): Promise<VehicleOwner> => {
    const res = await fetch(`${API_BASE}/api/owners/${numberPlate}`);
    if (!res.ok) throw new Error('Failed to fetch owner');
    return res.json();
  },
  
  addOwnerBalance: async (numberPlate: string, amount: number): Promise<{ newBalance: number }> => {
    const res = await fetch(`${API_BASE}/api/owners/${numberPlate}/add-balance?amount=${amount}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to add balance');
    return res.json();
  },
  
  // Revenue
  getRevenueStats: async (): Promise<RevenueStats> => {
    const res = await fetch(`${API_BASE}/api/revenue/stats`);
    if (!res.ok) throw new Error('Failed to fetch revenue stats');
    return res.json();
  },
  
  // Service Control
  getServiceStats: async (): Promise<AutoChallanServiceStats> => {
    const res = await fetch(`${API_BASE}/api/challan/service/stats`);
    if (!res.ok) throw new Error('Failed to fetch service stats');
    return res.json();
  },
  
  startService: async (): Promise<{ status: string; message: string }> => {
    const res = await fetch(`${API_BASE}/api/challan/service/start`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to start service');
    return res.json();
  },
  
  stopService: async (): Promise<{ status: string; message: string }> => {
    const res = await fetch(`${API_BASE}/api/challan/service/stop`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to stop service');
    return res.json();
  },
  
  forceProcess: async (): Promise<{ status: string; stats: AutoChallanServiceStats }> => {
    const res = await fetch(`${API_BASE}/api/challan/service/process`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to force process');
    return res.json();
  }
};


// ============================================
// Utility Functions
// ============================================

export const getViolationColor = (type: ViolationType): string => {
  const colors: Record<ViolationType, string> = {
    RED_LIGHT: '#ef4444',  // red
    SPEEDING: '#f97316',   // orange
    WRONG_DIRECTION: '#eab308',  // yellow
    WRONG_LANE: '#eab308',
    NO_STOPPING: '#22c55e'  // green
  };
  return colors[type] || '#6b7280';
};

export const getSeverityColor = (severity: ViolationSeverity): string => {
  const colors: Record<ViolationSeverity, string> = {
    HIGH: '#ef4444',    // red
    MEDIUM: '#f97316',  // orange
    LOW: '#22c55e'      // green
  };
  return colors[severity] || '#6b7280';
};

export const getStatusColor = (status: ChallanStatus): string => {
  const colors: Record<ChallanStatus, string> = {
    ISSUED: '#3b82f6',   // blue
    PAID: '#22c55e',     // green
    PENDING: '#f97316',  // orange
    CANCELLED: '#6b7280' // gray
  };
  return colors[status] || '#6b7280';
};

export const formatFine = (amount: number): string => {
  return `₹${amount.toLocaleString('en-IN')}`;
};

export const formatViolationType = (type: ViolationType): string => {
  const labels: Record<ViolationType, string> = {
    RED_LIGHT: 'Red Light Violation',
    SPEEDING: 'Speeding',
    WRONG_DIRECTION: 'Wrong Direction',
    WRONG_LANE: 'Wrong Lane',
    NO_STOPPING: 'No Stopping'
  };
  return labels[type] || type;
};

