import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LogOut, ShieldCheck } from 'lucide-react';
import { useAuth } from '../lib/auth-context';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

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

          {/* Navigation Links based on role */}
          {user && (
            <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
              {user.role === 'admin' && (
                <>
                  <Link
                    to="/admin/approvals"
                    className="px-3 py-1.5 rounded-[6px] text-[#4d4d4d] hover:text-[#171717] hover:bg-[#fafafa] transition-colors"
                  >
                    Approvals Queue
                  </Link>
                  <Link
                    to="/admin/audit"
                    className="px-3 py-1.5 rounded-[6px] text-[#4d4d4d] hover:text-[#171717] hover:bg-[#fafafa] transition-colors"
                  >
                    Audit Log
                  </Link>
                </>
              )}
              {user.role === 'company' && (
                <>
                  <Link
                    to="/company"
                    className="px-3 py-1.5 rounded-[6px] text-[#4d4d4d] hover:text-[#171717] hover:bg-[#fafafa] transition-colors"
                  >
                    Dashboard
                  </Link>
                </>
              )}
              {user.role === 'student' && (
                <>
                  <Link
                    to="/student"
                    className="px-3 py-1.5 rounded-[6px] text-[#4d4d4d] hover:text-[#171717] hover:bg-[#fafafa] transition-colors"
                  >
                    Projects
                  </Link>
                </>
              )}
              {user.role === 'recruiter' && (
                <>
                  <Link
                    to="/recruiter"
                    className="px-3 py-1.5 rounded-[6px] text-[#4d4d4d] hover:text-[#171717] hover:bg-[#fafafa] transition-colors"
                  >
                    Candidates
                  </Link>
                </>
              )}
            </nav>
          )}
        </div>

        {/* User profile / Auth buttons */}
        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-3">
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

              <button
                onClick={handleLogout}
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
