import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { RaxelLogo } from './RaxelLogo';
import { 
  MessageSquare, 
  FileText, 
  UploadCloud, 
  ShieldCheck, 
  Activity, 
  Database, 
  Users, 
  CheckCircle,
  X
} from 'lucide-react';

export const Sidebar = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const role = user?.role || 'student';
  const isAuth = user?.authenticated;

  const navLinkClasses = ({ isActive }) =>
    `flex items-center gap-2.5 px-3 py-2 rounded-sm text-xs sm:text-sm font-medium transition-all ${
      isActive
        ? 'text-raxel-indigo bg-raxel-violet-soft border-l-2 border-raxel-indigo font-semibold'
        : 'text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-surface-subtle border-l-2 border-transparent'
    }`;

  const sidebarContent = (
    <div className="flex flex-col gap-5 p-4">
      {/* Mobile Drawer Header */}
      <div className="flex items-center justify-between mb-1">
        <RaxelLogo size="sm" showText={true} />
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-surface-subtle transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Student Links */}
      <div>
        <div className="text-[11px] font-bold uppercase text-raxel-faint tracking-wider px-2 mb-1.5">
          Knowledge Assistant
        </div>
        <NavLink to="/student" className={navLinkClasses} onClick={onClose}>
          <MessageSquare className="w-4 h-4" />
          <span>Student Chat</span>
        </NavLink>
        <NavLink to="/student/sources" className={navLinkClasses} onClick={onClose}>
          <FileText className="w-4 h-4" />
          <span>Knowledge Sources</span>
        </NavLink>
      </div>

      {/* Faculty Links */}
      {(role === 'faculty' || role === 'admin') && isAuth && (
        <div>
          <div className="text-[11px] font-bold uppercase text-raxel-faint tracking-wider px-2 mb-1.5">
            Faculty Portal
          </div>
          <NavLink to="/faculty" className={navLinkClasses} onClick={onClose}>
            <FileText className="w-4 h-4" />
            <span>My Documents</span>
          </NavLink>
          <NavLink to="/faculty/upload" className={navLinkClasses} onClick={onClose}>
            <UploadCloud className="w-4 h-4" />
            <span>Upload Document</span>
          </NavLink>
        </div>
      )}

      {/* Admin Suite Links */}
      {role === 'admin' && isAuth && (
        <div>
          <div className="text-[11px] font-bold uppercase text-raxel-faint tracking-wider px-2 mb-1.5">
            Admin Governance Suite
          </div>
          <NavLink to="/admin" end className={navLinkClasses} onClick={onClose}>
            <Activity className="w-4 h-4" />
            <span>Dashboard</span>
          </NavLink>
          <NavLink to="/admin/approvals" className={navLinkClasses} onClick={onClose}>
            <CheckCircle className="w-4 h-4" />
            <span>Document Approvals</span>
          </NavLink>
          <NavLink to="/admin/users" className={navLinkClasses} onClick={onClose}>
            <Users className="w-4 h-4" />
            <span>Users & Roles</span>
          </NavLink>
          <NavLink to="/admin/quality" className={navLinkClasses} onClick={onClose}>
            <ShieldCheck className="w-4 h-4" />
            <span>Quality Control</span>
          </NavLink>
          <NavLink to="/admin/recovery" className={navLinkClasses} onClick={onClose}>
            <Database className="w-4 h-4" />
            <span>Health & Backup</span>
          </NavLink>
        </div>
      )}
    </div>
  );

  return (
    <aside className="w-60 border-r border-raxel-border bg-white flex flex-col min-h-[calc(100vh-64px)] shadow-sm">
      {sidebarContent}
    </aside>
  );
};

export default Sidebar;
