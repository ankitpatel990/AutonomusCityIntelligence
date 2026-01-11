/**
 * Challans Page
 * 
 * Dedicated page for viewing and managing traffic challans (e-challans)
 * Includes filtering, statistics, and payment status tracking
 */

import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Search, 
  Filter, 
  Download,
  CheckCircle,
  Clock,
  XCircle,
  RefreshCw,
  AlertTriangle,
  Car,
  MapPin,
  IndianRupee,
  TrendingUp,
  Calendar,
  Ban,
  Gauge
} from 'lucide-react';
import { api } from '../services/api';
import type { Challan } from '../types/models';

type ChallanStatus = 'ALL' | 'PENDING' | 'PAID' | 'CONTESTED' | 'CANCELLED';
type ViolationType = 'ALL' | 'RED_LIGHT' | 'SPEEDING' | 'WRONG_DIRECTION' | 'NO_HELMET' | 'NO_SEATBELT';

export const ChallansPage: React.FC = () => {
  const [challans, setChallans] = useState<Challan[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<ChallanStatus>('ALL');
  const [violationFilter, setViolationFilter] = useState<ViolationType>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    paid: 0,
    totalFines: 0,
    collectedFines: 0,
  });

  useEffect(() => {
    fetchChallans();
    fetchStats();
  }, [statusFilter]);

  const fetchChallans = async () => {
    setIsLoading(true);
    try {
      const status = statusFilter === 'ALL' ? undefined : statusFilter;
      const data = await api.getChallans(status);
      setChallans(data);
    } catch (error) {
      console.error('Failed to fetch challans:', error);
      setChallans(mockChallans);
    }
    setIsLoading(false);
  };

  const fetchStats = async () => {
    try {
      const data = await api.getChallanStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      setStats(mockStats);
    }
  };

  const filteredChallans = challans.filter(challan => {
    if (violationFilter !== 'ALL' && challan.violationType !== violationFilter) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        challan.numberPlate.toLowerCase().includes(query) ||
        challan.challanId.toLowerCase().includes(query) ||
        challan.location.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="p-6 space-y-6 min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <FileText className="w-7 h-7 text-blue-400" />
            E-Challans Management
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Auto-generated traffic violation challans
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg hover:bg-emerald-500/30 transition-all"
          >
            <Download className="w-4 h-4" />
            Export Report
          </button>
          <button
            onClick={fetchChallans}
            className="p-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition-all"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-5 gap-4">
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Total Challans</p>
              <p className="text-2xl font-bold text-white mt-1">{stats.total}</p>
            </div>
            <div className="bg-blue-500/10 p-2.5 rounded-lg">
              <FileText className="w-5 h-5 text-blue-400" />
            </div>
          </div>
        </div>
        
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Pending</p>
              <p className="text-2xl font-bold text-amber-400 mt-1">{stats.pending}</p>
            </div>
            <div className="bg-amber-500/10 p-2.5 rounded-lg">
              <Clock className="w-5 h-5 text-amber-400" />
            </div>
          </div>
        </div>
        
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Paid</p>
              <p className="text-2xl font-bold text-emerald-400 mt-1">{stats.paid}</p>
            </div>
            <div className="bg-emerald-500/10 p-2.5 rounded-lg">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            </div>
          </div>
        </div>
        
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Total Fines</p>
              <p className="text-xl font-bold text-white mt-1">{formatCurrency(stats.totalFines)}</p>
            </div>
            <div className="bg-purple-500/10 p-2.5 rounded-lg">
              <IndianRupee className="w-5 h-5 text-purple-400" />
            </div>
          </div>
        </div>
        
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Collected</p>
              <p className="text-xl font-bold text-emerald-400 mt-1">{formatCurrency(stats.collectedFines)}</p>
            </div>
            <div className="bg-emerald-500/10 p-2.5 rounded-lg">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Collection Progress */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-white">Fine Collection Progress</h3>
          <span className="text-sm text-emerald-400 font-bold">
            {stats.totalFines > 0 ? ((stats.collectedFines / stats.totalFines) * 100).toFixed(1) : 0}%
          </span>
        </div>
        <div className="h-3 bg-slate-700/50 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 rounded-full transition-all duration-500"
            style={{ width: `${stats.totalFines > 0 ? (stats.collectedFines / stats.totalFines) * 100 : 0}%` }}
          ></div>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by plate number, challan ID, or location..."
            className="w-full pl-10 pr-4 py-2.5 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as ChallanStatus)}
            className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 text-slate-300 focus:outline-none focus:border-cyan-500/50"
          >
            <option value="ALL">All Status</option>
            <option value="PENDING">Pending</option>
            <option value="PAID">Paid</option>
            <option value="CONTESTED">Contested</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
          
          <select
            value={violationFilter}
            onChange={(e) => setViolationFilter(e.target.value as ViolationType)}
            className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 text-slate-300 focus:outline-none focus:border-cyan-500/50"
          >
            <option value="ALL">All Violations</option>
            <option value="RED_LIGHT">Red Light</option>
            <option value="SPEEDING">Speeding</option>
            <option value="WRONG_DIRECTION">Wrong Direction</option>
            <option value="NO_HELMET">No Helmet</option>
            <option value="NO_SEATBELT">No Seatbelt</option>
          </select>
        </div>
      </div>

      {/* Challans Table */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-900/50">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Challan ID</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Vehicle</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Violation</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Location</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Date & Time</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Fine</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {filteredChallans.length > 0 ? (
              filteredChallans.map((challan) => (
                <ChallanRow key={challan.challanId} challan={challan} />
              ))
            ) : (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center">
                  <div className="flex flex-col items-center">
                    <FileText className="w-10 h-10 text-slate-500 mb-3" />
                    <p className="text-slate-400">No challans found</p>
                    <p className="text-sm text-slate-500">Try adjusting your filters</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Challan Row Component
const ChallanRow: React.FC<{ challan: Challan }> = ({ challan }) => {
  const getViolationIcon = (type: string) => {
    switch (type) {
      case 'RED_LIGHT':
        return <Ban className="w-4 h-4 text-red-400" />;
      case 'SPEEDING':
        return <Gauge className="w-4 h-4 text-amber-400" />;
      case 'WRONG_DIRECTION':
        return <AlertTriangle className="w-4 h-4 text-orange-400" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'PAID':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'PENDING':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'CONTESTED':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'CANCELLED':
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <tr className="hover:bg-slate-700/30 transition-colors">
      <td className="px-4 py-3">
        <span className="font-mono text-sm text-cyan-400">{challan.challanId}</span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <Car className="w-4 h-4 text-slate-400" />
          <span className="font-bold text-white">{challan.numberPlate}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          {getViolationIcon(challan.violationType)}
          <span className="text-sm text-slate-300">{challan.violationType.replace('_', ' ')}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 text-sm text-slate-400">
          <MapPin className="w-3 h-3" />
          {challan.location}
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 text-sm text-slate-400">
          <Calendar className="w-3 h-3" />
          {formatTime(challan.timestamp)}
        </div>
      </td>
      <td className="px-4 py-3 text-right">
        <span className="font-bold text-emerald-400">₹{challan.fineAmount}</span>
      </td>
      <td className="px-4 py-3 text-center">
        <span className={`text-xs px-2 py-1 rounded border ${getStatusStyle(challan.status)}`}>
          {challan.status}
        </span>
      </td>
    </tr>
  );
};

// Mock data for demo
const mockChallans: Challan[] = [
  {
    challanId: 'CH-2026-00001',
    violationId: 'V-001',
    numberPlate: 'GJ-01-AB-1234',
    violationType: 'RED_LIGHT',
    location: 'Junction J-005',
    timestamp: Date.now() / 1000 - 3600,
    fineAmount: 1000,
    status: 'PENDING',
    evidenceUrl: '',
    issuedAt: Date.now() / 1000 - 3600,
  },
  {
    challanId: 'CH-2026-00002',
    violationId: 'V-002',
    numberPlate: 'GJ-05-XY-7890',
    violationType: 'SPEEDING',
    location: 'Highway NH-48',
    timestamp: Date.now() / 1000 - 7200,
    fineAmount: 2000,
    status: 'PAID',
    evidenceUrl: '',
    issuedAt: Date.now() / 1000 - 7200,
  },
  {
    challanId: 'CH-2026-00003',
    violationId: 'V-003',
    numberPlate: 'GJ-18-CD-4567',
    violationType: 'WRONG_DIRECTION',
    location: 'One-way Road R-007',
    timestamp: Date.now() / 1000 - 14400,
    fineAmount: 1500,
    status: 'CONTESTED',
    evidenceUrl: '',
    issuedAt: Date.now() / 1000 - 14400,
  },
  {
    challanId: 'CH-2026-00004',
    violationId: 'V-004',
    numberPlate: 'GJ-06-EF-2345',
    violationType: 'RED_LIGHT',
    location: 'Junction J-002',
    timestamp: Date.now() / 1000 - 28800,
    fineAmount: 1000,
    status: 'PAID',
    evidenceUrl: '',
    issuedAt: Date.now() / 1000 - 28800,
  },
  {
    challanId: 'CH-2026-00005',
    violationId: 'V-005',
    numberPlate: 'GJ-01-GH-9876',
    violationType: 'SPEEDING',
    location: 'Ring Road',
    timestamp: Date.now() / 1000 - 43200,
    fineAmount: 2500,
    status: 'PENDING',
    evidenceUrl: '',
    issuedAt: Date.now() / 1000 - 43200,
  },
];

const mockStats = {
  total: 156,
  pending: 45,
  paid: 98,
  totalFines: 234500,
  collectedFines: 178200,
};

