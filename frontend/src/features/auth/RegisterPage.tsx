import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, Building2, CheckCircle2, GraduationCap, Loader2, UserCheck } from 'lucide-react';
import { apiRequest } from '../../lib/api';
import { useAuth } from '../../lib/auth-context';

export const RegisterPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [role, setRole] = useState<'student' | 'company' | 'recruiter'>('student');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [website, setWebsite] = useState('');
  const [description, setDescription] = useState('');
  const [organization, setOrganization] = useState('');

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [registeredSuccess, setRegisteredSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (password.length < 10) {
        throw new Error('Password must be at least 10 characters long.');
      }

      // Step 1: Register account
      await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
          role,
          full_name: role === 'student' ? fullName : undefined,
          organization: role === 'recruiter' ? organization : undefined,
        }),
      });

      // Step 2: Login to complete profile setup if company or recruiter
      const loggedUser = await login(email, password);

      if (role === 'company') {
        await apiRequest('/companies/json', {
          method: 'POST',
          body: JSON.stringify({
            name: companyName,
            website: website || undefined,
            description: description || undefined,
          }),
        });
      } else if (role === 'recruiter') {
        await apiRequest('/recruiters', {
          method: 'POST',
          body: JSON.stringify({
            full_name: fullName,
            organization,
          }),
        });
      }

      setRegisteredSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please check your information.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (registeredSuccess) {
    return (
      <div className="min-h-[calc(100vh-3.5rem)] flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-[#fafafa]">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-[#ffffff] p-8 border border-[#ebebeb] rounded-[6px] text-center shadow-sm">
            <CheckCircle2 className="w-12 h-12 text-[#15803d] mx-auto mb-4" />
            <h2 className="text-xl font-bold text-[#171717] mb-2">Account Created!</h2>
            <p className="text-sm text-[#4d4d4d] mb-4">
              We have created your <strong>{role}</strong> account for <span className="font-mono text-xs">{email}</span>.
            </p>
            <div className="p-3 bg-[#fafafa] border border-[#ebebeb] rounded-[6px] text-xs font-mono text-[#7d7d7d] mb-6 text-left">
              FR-AUTH-2 Notice: Email must be verified before performing actions beyond viewing your profile.
            </div>
            <button
              onClick={() => {
                if (role === 'company') navigate('/company');
                else if (role === 'recruiter') navigate('/recruiter');
                else navigate('/student');
              }}
              className="w-full py-2 px-4 rounded-[6px] bg-[#171717] hover:bg-[#000000] text-[#ffffff] text-sm font-medium transition-colors"
            >
              Continue to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-[#fafafa]">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <span className="text-[#171717] font-black text-2xl select-none">▲</span>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold tracking-tight text-[#171717]">
          Create your account
        </h2>
        <p className="mt-1 text-center text-xs font-mono text-[#7d7d7d]">
          Join ProjectProof to build and verify real-world project experience
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-[#ffffff] py-8 px-6 shadow-sm border border-[#ebebeb] rounded-[6px] sm:px-8">
          {/* Role selector tabs */}
          <div className="grid grid-cols-3 gap-1 p-1 bg-[#fafafa] border border-[#ebebeb] rounded-[6px] mb-6">
            <button
              type="button"
              onClick={() => setRole('student')}
              className={`flex items-center justify-center gap-1.5 py-1.5 px-2 text-xs font-medium rounded-[4px] transition-colors ${
                role === 'student' ? 'bg-[#ffffff] text-[#171717] shadow-sm' : 'text-[#7d7d7d] hover:text-[#171717]'
              }`}
            >
              <GraduationCap className="w-3.5 h-3.5" />
              <span>Student</span>
            </button>
            <button
              type="button"
              onClick={() => setRole('company')}
              className={`flex items-center justify-center gap-1.5 py-1.5 px-2 text-xs font-medium rounded-[4px] transition-colors ${
                role === 'company' ? 'bg-[#ffffff] text-[#171717] shadow-sm' : 'text-[#7d7d7d] hover:text-[#171717]'
              }`}
            >
              <Building2 className="w-3.5 h-3.5" />
              <span>Company</span>
            </button>
            <button
              type="button"
              onClick={() => setRole('recruiter')}
              className={`flex items-center justify-center gap-1.5 py-1.5 px-2 text-xs font-medium rounded-[4px] transition-colors ${
                role === 'recruiter' ? 'bg-[#ffffff] text-[#171717] shadow-sm' : 'text-[#7d7d7d] hover:text-[#171717]'
              }`}
            >
              <UserCheck className="w-3.5 h-3.5" />
              <span>Recruiter</span>
            </button>
          </div>

          {error && (
            <div className="mb-6 p-3 rounded-[6px] bg-[#fef2f2] border border-[#fecaca] flex items-start gap-2.5 text-xs text-[#991b1b]">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {role === 'student' && (
              <div>
                <label className="block text-xs font-mono uppercase tracking-wider text-[#4d4d4d] mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Ananya Sharma"
                  className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717]"
                />
              </div>
            )}

            {role === 'company' && (
              <>
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-[#4d4d4d] mb-1.5">
                    Company Name
                  </label>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. Nova Labs Inc."
                    className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-[#4d4d4d] mb-1.5">
                    Company Website
                  </label>
                  <input
                    type="url"
                    value={website}
                    onChange={(e) => setWebsite(e.target.value)}
                    placeholder="https://novalabs.com"
                    className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-[#4d4d4d] mb-1.5">
                    Company Description
                  </label>
                  <textarea
                    rows={2}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Brief description of your engineering projects..."
                    className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717]"
                  />
                </div>
              </>
            )}

            {role === 'recruiter' && (
              <>
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-[#4d4d4d] mb-1.5">
                    Your Full Name
                  </label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Vikram Mehta"
                    className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-[#4d4d4d] mb-1.5">
                    Hiring Organization
                  </label>
                  <input
                    type="text"
                    required
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                    placeholder="e.g. Apex Talent Search"
                    className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717]"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-[#4d4d4d] mb-1.5">
                {role === 'company' || role === 'recruiter' ? 'Work Email' : 'Email Address'}
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={role === 'company' ? 'contact@company.com' : 'name@example.com'}
                className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717]"
              />
              {role === 'company' && (
                <p className="mt-1 text-[11px] text-[#7d7d7d]">
                  Work domain will be automatically checked against your website.
                </p>
              )}
            </div>

            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-[#4d4d4d] mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                minLength={10}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 10 characters"
                className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717]"
              />
              <p className="mt-1 text-[11px] text-[#7d7d7d]">
                At least 10 characters. Checked against common passwords list.
              </p>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-4 flex items-center justify-center gap-2 py-2 px-4 rounded-[6px] bg-[#171717] hover:bg-[#000000] text-[#ffffff] text-sm font-medium transition-colors disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Creating Account...</span>
                </>
              ) : (
                <span>Register as {role}</span>
              )}
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-[#7d7d7d]">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-[#171717] hover:underline">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
