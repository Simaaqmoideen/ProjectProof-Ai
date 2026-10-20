import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
import { useAuth } from '../../lib/auth-context';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const user = await login(email, password);
      // Route based on role
      switch (user.role) {
        case 'admin':
          navigate('/admin/approvals');
          break;
        case 'company':
          navigate('/company');
          break;
        case 'recruiter':
          navigate('/recruiter');
          break;
        default:
          navigate('/student');
          break;
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
  };

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-[#fafafa]">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <span className="text-[#171717] font-black text-2xl select-none">▲</span>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold tracking-tight text-[#171717]">
          Sign in to ProjectProof
        </h2>
        <p className="mt-1 text-center text-xs font-mono text-[#7d7d7d]">
          Live project proof and cryptographic verification
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-[#ffffff] py-8 px-6 shadow-sm border border-[#ebebeb] rounded-[6px] sm:px-8">
          {error && (
            <div className="mb-6 p-3 rounded-[6px] bg-[#fef2f2] border border-[#fecaca] flex items-start gap-2.5 text-xs text-[#991b1b]">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-mono uppercase tracking-wider text-[#4d4d4d] mb-1.5">
                Work or College Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717] transition-colors"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="password" className="block text-xs font-mono uppercase tracking-wider text-[#4d4d4d]">
                  Password
                </label>
                <Link to="/forgot-password" className="text-xs text-[#7d7d7d] hover:text-[#171717]">
                  Forgot?
                </Link>
              </div>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717] transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 flex items-center justify-center gap-2 py-2 px-4 rounded-[6px] bg-[#171717] hover:bg-[#000000] text-[#ffffff] text-sm font-medium transition-colors disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Demo 1-click accounts - hidden unless DEMO_MODE=true */}
          {((import.meta.env.DEMO_MODE === 'true') || (import.meta.env.VITE_DEMO_MODE === 'true')) && (
            <div className="mt-6 pt-6 border-t border-[#ebebeb]">
              <p className="text-[11px] font-mono uppercase tracking-wider text-[#8f8f8f] mb-2.5 text-center">
                Quick demo accounts:
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <button
                  type="button"
                  onClick={() => handleQuickLogin('admin@projectproof.ai', 'AdminSecure2026!')}
                  className="px-2.5 py-1.5 text-left border border-[#ebebeb] rounded-[4px] hover:bg-[#fafafa] transition-colors"
                >
                  <span className="font-semibold block text-[#171717]">Admin</span>
                  <span className="font-mono text-[10px] text-[#7d7d7d]">Platform review</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin('contact@novalabs.com', 'NovaLabs2026!')}
                  className="px-2.5 py-1.5 text-left border border-[#ebebeb] rounded-[4px] hover:bg-[#fafafa] transition-colors"
                >
                  <span className="font-semibold block text-[#171717]">Company</span>
                  <span className="font-mono text-[10px] text-[#7d7d7d]">Approved</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin('ananya@example.com', 'StudentPass2026!')}
                  className="px-2.5 py-1.5 text-left border border-[#ebebeb] rounded-[4px] hover:bg-[#fafafa] transition-colors"
                >
                  <span className="font-semibold block text-[#171717]">Student</span>
                  <span className="font-mono text-[10px] text-[#7d7d7d]">Verified</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin('recruiter@apexsearch.com', 'Recruiter2026!')}
                  className="px-2.5 py-1.5 text-left border border-[#ebebeb] rounded-[4px] hover:bg-[#fafafa] transition-colors"
                >
                  <span className="font-semibold block text-[#171717]">Recruiter</span>
                  <span className="font-mono text-[10px] text-[#7d7d7d]">Apex Search</span>
                </button>
              </div>
            </div>
          )}

          <div className="mt-6 text-center text-xs text-[#7d7d7d]">
            Don't have an account?{' '}
            <Link to="/register" className="font-medium text-[#171717] hover:underline">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
