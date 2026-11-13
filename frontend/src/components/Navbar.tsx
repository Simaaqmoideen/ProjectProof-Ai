import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell, LogOut, ShieldCheck, User } from 'lucide-react';
import { useAuth } from '../lib/auth-context';
import { apiRequest } from '../lib/api';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);

  // Poll unread count every 60 s while logged in
  useEffect(() => {
    if (!user) {
      setUnreadCount(0);
      return;
    }

    const fetchCount = async () => {
      try {
        const res = await apiRequest<{ unread_count: number }>('/notifications/unread-count');
        setUnreadCount(res.unread_count ?? 0);
      } catch {
        // ignore
      }
    };

    fetchCount();
    const timer = setInterval(fetchCount, 60_000);
    return () => clearInterval(timer);
  }, [user]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navLink =
    'px-3 py-1.5 rounded-[6px] text-[#4d4d4d] hover:text-[#171717] hover:bg-[#fafafa] transition-colors';

  return (
    <header className="border-b border-[#ebebeb] bg-[#ffffff] sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 group">
            <span className="text-[#171717] font-black text-lg select-none group-hover:opacity-80 transition-opacity">
              ▲
            </span>
            <div className="flex flex-col">
              <span className="font-semibold text-sm tracking-tight text-[#171717]">
                ProjectProof
              </span>
              <span className="text-[10px] font-mono uppercase tracking-wider text-[#8f8f8f] -mt-1">
                AI Platform
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium" aria-label="Main">
            <Link to="/projects" className={navLink}>
              Browse Projects
            </Link>

            {user && (
              <>
                {user.role === 'admin' && (
                  <>
                    <Link to="/admin/approvals" className={navLink}>
                      Approvals Queue
                    </Link>
                    <Link to="/admin/audit" className={navLink}>
                      Audit Log
                    </Link>
                  </>
                )}
                {user.role === 'company' && (
                  <Link to="/company" className={navLink}>
                    Dashboard
                  </Link>
                )}
                {user.role === 'student' && (
                  <>
                    <Link to="/student" className={navLink}>
                      Dashboard
                    </Link>
                    <Link to="/student/portfolio" className={navLink}>
                      Portfolio
                    </Link>
                  </>
                )}
                {user.role === 'recruiter' && (
                  <Link to="/recruiter" className={navLink}>
                    Candidates
                  </Link>
                )}
              </>
            )}
          </nav>
        </div>

        {/* User profile / Auth buttons */}
        <div className="flex items-center gap-2">
          {user ? (
            <div className="flex items-center gap-2">
              {/* User chip */}
              <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-[6px] border border-[#ebebeb] bg-[#fafafa] text-xs">
                <span className="font-mono text-[#171717] truncate max-w-[160px]">
                  {user.email}
                </span>
                <span className="px-1.5 py-0.5 rounded-[4px] bg-[#171717] text-[#ffffff] uppercase text-[9px] font-mono tracking-wider">
                  {user.role}
                </span>
                {user.email_verified && (
                  <span title="Email verified">
                    <ShieldCheck className="w-3.5 h-3.5 text-[#15803d]" />
                  </span>
                )}
              </div>

              {/* Notifications bell */}
              <Link
                to="/notifications"
                id="notifications-bell"
                aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
                className="relative p-2 rounded-[6px] text-[#4d4d4d] hover:text-[#171717] hover:bg-[#fafafa] border border-[#ebebeb] transition-colors"
              >
                <Bell className="w-3.5 h-3.5" />
                {unreadCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 min-w-[14px] h-[14px] flex items-center justify-center rounded-full bg-[#171717] text-white text-[9px] font-mono px-0.5">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </Link>

              {/* Profile link (student only) */}
              {user.role === 'student' && (
                <Link
                  to="/student/profile"
                  id="student-profile-link"
                  aria-label="My profile"
                  className="p-2 rounded-[6px] text-[#4d4d4d] hover:text-[#171717] hover:bg-[#fafafa] border border-[#ebebeb] transition-colors"
                >
                  <User className="w-3.5 h-3.5" />
                </Link>
              )}

              <button
                onClick={handleLogout}
                id="logout-btn"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] text-xs font-medium text-[#4d4d4d] hover:text-[#171717] hover:bg-[#fafafa] border border-[#ebebeb] transition-colors"
                title="Log out"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="px-3 py-1.5 rounded-[6px] text-xs font-medium text-[#171717] hover:bg-[#fafafa] border border-[#ebebeb] transition-colors"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="px-3 py-1.5 rounded-[6px] text-xs font-medium text-[#ffffff] bg-[#171717] hover:bg-[#000000] transition-colors"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
