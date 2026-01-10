/**
 * Sidebar Component
 * 
 * Navigation sidebar with links to different sections
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Shield, 
  BarChart3, 
  AlertTriangle, 
  FileText,
  Car,
  Map,
  Settings,
  Radio
} from 'lucide-react';

interface NavItem {
  path: string;
  label: string;
  icon: React.ElementType;
  badge?: number | string;
  badgeColor?: string;
}

export const Sidebar: React.FC = () => {
  const location = useLocation();

  const navItems: NavItem[] = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/map', label: 'City Map', icon: Map },
    { path: '/vehicles', label: 'Vehicles', icon: Car },
    { path: '/safety', label: 'Safety', icon: Shield },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/incidents', label: 'Incidents', icon: AlertTriangle, badge: '!', badgeColor: 'bg-amber-500' },
    { path: '/challans', label: 'Challans', icon: FileText },
    { path: '/emergency', label: 'Emergency', icon: Radio },
  ];

  const bottomItems: NavItem[] = [
    { path: '/settings', label: 'Settings', icon: Settings },
  ];

  const isActive = (path: string) => location.pathname === path;

  const NavLink: React.FC<{ item: NavItem }> = ({ item }) => {
    const Icon = item.icon;
    const active = isActive(item.path);

    return (
      <Link
        to={item.path}
        className={`
          relative flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200
          ${active 
            ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-400 shadow-lg shadow-cyan-500/10' 
            : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
          }
        `}
      >
        {/* Active indicator */}
        {active && (
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-r-full"></div>
        )}
        
        <Icon className={`w-5 h-5 ${active ? 'text-cyan-400' : ''}`} />
        <span className="font-medium">{item.label}</span>
        
        {/* Badge */}
        {item.badge && (
          <span className={`ml-auto px-2 py-0.5 text-xs font-bold rounded-full ${item.badgeColor || 'bg-slate-600'} text-white`}>
            {item.badge}
          </span>
        )}
      </Link>
    );
  };

  return (
    <aside className="w-64 bg-slate-900/50 backdrop-blur-sm border-r border-slate-700/50 flex flex-col">
      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <div className="mb-6">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 mb-2">
            Navigation
          </h3>
          {navItems.map((item) => (
            <NavLink key={item.path} item={item} />
          ))}
        </div>
      </nav>

      {/* Bottom Section */}
      <div className="p-4 border-t border-slate-700/50">
        {bottomItems.map((item) => (
          <NavLink key={item.path} item={item} />
        ))}
        
        {/* Version Info */}
        <div className="mt-4 px-4 py-2 text-center">
          <p className="text-xs text-slate-600">
            AutonomousHacks 2026
          </p>
          <p className="text-[10px] text-slate-700">
            v2.0 • RL-Core Edition
          </p>
        </div>
      </div>
    </aside>
  );
};

