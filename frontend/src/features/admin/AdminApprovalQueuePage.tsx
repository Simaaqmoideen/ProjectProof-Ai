import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Building2,
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileCheck,
  FileText,
  Filter,
  History,
  Info,
  Loader2,
  RotateCw,
  Search,
  Shield,
  ShieldAlert,
  UserCheck,
  X,
  XCircle,
} from 'lucide-react';
import { apiRequest } from '../../lib/api';
import { StatusBadge } from '../../components/StatusBadge';

interface AutomatedChecks {
  domain_matches_website: boolean;
  document_uploaded: boolean;
  domain_conflict: boolean;
  is_free_email: boolean;
}

interface CompanyItem {
  id: string;
  name: string;
  website: string | null;
  email_domain: string | null;
  description: string | null;
  registration_doc_key: string | null;
  status: string;
  trust_score: number;
  created_at: string;
  owner_email: string | null;
  automated_checks: AutomatedChecks;
}

interface RecruiterItem {
  user_id: string;
  full_name: string;
  organization: string;
  work_email_domain: string | null;
  email: string;
  status: string;
  created_at: string;
}

interface AuditItem {
  id: number;
  actor_id: string | null;
  actor_email: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  detail: any;
  created_at: string;
}

interface AdminApprovalQueueProps {
  defaultTab?: 'companies' | 'recruiters' | 'audit';
}

export const AdminApprovalQueuePage: React.FC<AdminApprovalQueueProps> = ({ defaultTab = 'companies' }) => {
  const [activeTab, setActiveTab] = useState<'companies' | 'recruiters' | 'audit'>(defaultTab);

  // Companies state
  const [companies, setCompanies] = useState<CompanyItem[]>([]);
  const [companyStatusFilter, setCompanyStatusFilter] = useState<string>('pending');
  const [loadingCompanies, setLoadingCompanies] = useState(false);

  // Recruiters state
  const [recruiters, setRecruiters] = useState<RecruiterItem[]>([]);
  const [recruiterStatusFilter, setRecruiterStatusFilter] = useState<string>('pending');
  const [loadingRecruiters, setLoadingRecruiters] = useState(false);

  // Audit state
  const [auditLogs, setAuditLogs] = useState<AuditItem[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);

  // Action modals
  const [rejectModal, setRejectModal] = useState<{ open: boolean; type: 'company' | 'recruiter'; id: string; name: string } | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchCompanies = async () => {
    setLoadingCompanies(true);
    try {
      const query = companyStatusFilter ? `?status=${companyStatusFilter}` : '';
      const data = await apiRequest<CompanyItem[]>(`/admin/companies${query}`);
      setCompanies(data);
    } catch (err: any) {
      setActionMessage({ text: err.message || 'Failed to load companies', type: 'error' });
    } finally {
      setLoadingCompanies(false);
    }
  };

  const fetchRecruiters = async () => {
    setLoadingRecruiters(true);
    try {
      const query = recruiterStatusFilter ? `?status=${recruiterStatusFilter}` : '';
      const data = await apiRequest<RecruiterItem[]>(`/admin/recruiters${query}`);
      setRecruiters(data);
    } catch (err: any) {
      setActionMessage({ text: err.message || 'Failed to load recruiters', type: 'error' });
    } finally {
      setLoadingRecruiters(false);
    }
  };

  const fetchAuditLogs = async () => {
    setLoadingAudit(true);
    try {
      const data = await apiRequest<{ items: AuditItem[] }>('/admin/audit-log?page=1&page_size=50');
      setAuditLogs(data.items);
    } catch (err: any) {
      setActionMessage({ text: err.message || 'Failed to load audit logs', type: 'error' });
    } finally {
      setLoadingAudit(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'companies') fetchCompanies();
    else if (activeTab === 'recruiters') fetchRecruiters();
    else if (activeTab === 'audit') fetchAuditLogs();
  }, [activeTab, companyStatusFilter, recruiterStatusFilter]);

  const handleApproveCompany = async (companyId: string, companyName: string) => {
    setIsProcessing(true);
    try {
      await apiRequest(`/admin/companies/${companyId}/approve`, { method: 'POST' });
      setActionMessage({ text: `Approved company "${companyName}" successfully.`, type: 'success' });
      fetchCompanies();
    } catch (err: any) {
      setActionMessage({ text: err.message || 'Approval failed.', type: 'error' });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSuspendCompany = async (companyId: string, companyName: string) => {
    if (!confirm(`Are you sure you want to suspend "${companyName}"? Open projects will be closed.`)) return;
    setIsProcessing(true);
    try {
      await apiRequest(`/admin/companies/${companyId}/suspend`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'Admin suspended company' }),
      });
      setActionMessage({ text: `Suspended company "${companyName}". Open projects closed.`, type: 'success' });
      fetchCompanies();
    } catch (err: any) {
      setActionMessage({ text: err.message || 'Suspension failed.', type: 'error' });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApproveRecruiter = async (userId: string, name: string) => {
    setIsProcessing(true);
    try {
      await apiRequest(`/admin/recruiters/${userId}/approve`, { method: 'POST' });
      setActionMessage({ text: `Approved recruiter "${name}" successfully.`, type: 'success' });
      fetchRecruiters();
    } catch (err: any) {
      setActionMessage({ text: err.message || 'Approval failed.', type: 'error' });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirmReject = async () => {
    if (!rejectModal) return;
    setIsProcessing(true);
    try {
      if (rejectModal.type === 'company') {
        await apiRequest(`/admin/companies/${rejectModal.id}/reject`, {
          method: 'POST',
          body: JSON.stringify({ reason: rejectionReason }),
        });
        setActionMessage({ text: `Rejected company "${rejectModal.name}".`, type: 'success' });
        fetchCompanies();
      } else {
        await apiRequest(`/admin/recruiters/${rejectModal.id}/reject`, {
          method: 'POST',
          body: JSON.stringify({ reason: rejectionReason }),
        });
        setActionMessage({ text: `Rejected recruiter "${rejectModal.name}".`, type: 'success' });
        fetchRecruiters();
      }
      setRejectModal(null);
      setRejectionReason('');
    } catch (err: any) {
      setActionMessage({ text: err.message || 'Rejection failed.', type: 'error' });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#fafafa] pb-16">
      {/* Top Header */}
      <div className="bg-[#ffffff] border-b border-[#ebebeb] py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-[#171717]" />
                <h1 className="text-xl font-bold tracking-tight text-[#171717]">
                  Admin Review & Operations
                </h1>
              </div>
              <p className="mt-1 text-xs font-mono text-[#7d7d7d]">
                Automated domain verifications, company trust scoring, and tamper-evident audit log
              </p>
            </div>

            {/* Tab switchers */}
            <div className="flex items-center p-1 bg-[#fafafa] border border-[#ebebeb] rounded-[6px]">
              <button
                onClick={() => setActiveTab('companies')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-[4px] transition-colors ${
                  activeTab === 'companies' ? 'bg-[#ffffff] text-[#171717] shadow-sm' : 'text-[#7d7d7d] hover:text-[#171717]'
                }`}
              >
                <Building2 className="w-3.5 h-3.5" />
                <span>Companies</span>
              </button>

              <button
                onClick={() => setActiveTab('recruiters')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-[4px] transition-colors ${
                  activeTab === 'recruiters' ? 'bg-[#ffffff] text-[#171717] shadow-sm' : 'text-[#7d7d7d] hover:text-[#171717]'
                }`}
              >
                <UserCheck className="w-3.5 h-3.5" />
                <span>Recruiters</span>
              </button>

              <button
                onClick={() => setActiveTab('audit')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-[4px] transition-colors ${
                  activeTab === 'audit' ? 'bg-[#ffffff] text-[#171717] shadow-sm' : 'text-[#7d7d7d] hover:text-[#171717]'
                }`}
              >
                <History className="w-3.5 h-3.5" />
                <span>Audit Log</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        {/* Flash banner */}
        {actionMessage && (
          <div
            className={`mb-6 p-3 rounded-[6px] text-xs flex items-center justify-between border ${
              actionMessage.type === 'success'
                ? 'bg-[#f0fdf4] text-[#15803d] border-[#bbf7d0]'
                : 'bg-[#fef2f2] text-[#991b1b] border-[#fecaca]'
            }`}
          >
            <span>{actionMessage.text}</span>
            <button onClick={() => setActionMessage(null)} className="hover:opacity-75">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ===================== TAB 1: COMPANIES ===================== */}
        {activeTab === 'companies' && (
          <div>
            {/* Filter Bar */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-mono uppercase text-[#7d7d7d]">Filter:</span>
                {(['pending', 'approved', 'rejected', 'suspended'] as const).map((st) => (
                  <button
                    key={st}
                    onClick={() => setCompanyStatusFilter(st)}
                    className={`px-2.5 py-1 rounded-[4px] font-mono text-xs capitalize transition-colors ${
                      companyStatusFilter === st
                        ? 'bg-[#171717] text-[#ffffff]'
                        : 'bg-[#ffffff] text-[#7d7d7d] border border-[#ebebeb] hover:text-[#171717]'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              <button
                onClick={fetchCompanies}
                className="flex items-center gap-1 px-2.5 py-1 rounded-[4px] text-xs border border-[#ebebeb] bg-[#ffffff] hover:bg-[#fafafa]"
              >
                <RotateCw className="w-3 h-3" />
                <span>Refresh</span>
              </button>
            </div>

            {loadingCompanies ? (
              <div className="py-16 text-center text-[#7d7d7d] text-sm flex flex-col items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin mb-2" />
                <span>Loading company approval queue...</span>
              </div>
            ) : companies.length === 0 ? (
              <div className="py-16 text-center bg-[#ffffff] border border-[#ebebeb] rounded-[6px]">
                <Building2 className="w-10 h-10 text-[#a8a8a8] mx-auto mb-2" />
                <p className="text-sm font-medium text-[#171717]">No companies in queue</p>
                <p className="text-xs text-[#7d7d7d] mt-1 font-mono">Status: {companyStatusFilter}</p>
              </div>
            ) : (
              <div className="space-y-4">
                {companies.map((company) => (
                  <div
                    key={company.id}
                    className="bg-[#ffffff] border border-[#ebebeb] rounded-[6px] p-5 shadow-sm transition-all hover:border-[#c9c9c9]"
                  >
                    <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                      {/* Company Info */}
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1.5">
                          <h2 className="text-base font-bold text-[#171717]">{company.name}</h2>
                          <StatusBadge status={company.status} />
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[4px] bg-[#fafafa] border border-[#ebebeb] text-[11px] font-mono text-[#4d4d4d]">
                            Trust Score: <strong>{company.trust_score}/100</strong>
                          </span>
                        </div>

                        {company.description && (
                          <p className="text-xs text-[#4d4d4d] mb-3 line-clamp-2">
                            {company.description}
                          </p>
                        )}

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs font-mono text-[#7d7d7d]">
                          {company.website && (
                            <a
                              href={company.website}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-[#171717] hover:underline"
                            >
                              <span>{company.website}</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                          <span>Owner: {company.owner_email || 'None'}</span>
                          <span>Domain: {company.email_domain || 'N/A'}</span>
                          <span>Registered: {new Date(company.created_at).toLocaleDateString()}</span>
                        </div>

                        {/* Automated Checks Panel (FR-ORG-3) */}
                        <div className="mt-4 p-3 bg-[#fafafa] border border-[#ebebeb] rounded-[6px]">
                          <div className="flex items-center gap-1.5 mb-2">
                            <ShieldAlert className="w-3.5 h-3.5 text-[#171717]" />
                            <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-[#171717]">
                              Automated Pre-Approval Checks
                            </span>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                            {/* Check 1: Domain Matches Website */}
                            <div className="flex items-center gap-2 p-2 rounded-[4px] bg-[#ffffff] border border-[#ebebeb]">
                              {company.automated_checks.domain_matches_website ? (
                                <CheckCircle2 className="w-4 h-4 text-[#15803d] shrink-0" />
                              ) : (
                                <XCircle className="w-4 h-4 text-[#b91c1c] shrink-0" />
                              )}
                              <div className="flex flex-col">
                                <span className="font-medium text-[#171717]">Domain Match</span>
                                <span className="text-[10px] text-[#7d7d7d] font-mono">
                                  {company.automated_checks.domain_matches_website ? 'Verified' : 'Mismatch'}
                                </span>
                              </div>
                            </div>

                            {/* Check 2: Document Uploaded */}
                            <div className="flex items-center gap-2 p-2 rounded-[4px] bg-[#ffffff] border border-[#ebebeb]">
                              {company.automated_checks.document_uploaded ? (
                                <CheckCircle2 className="w-4 h-4 text-[#15803d] shrink-0" />
                              ) : (
                                <XCircle className="w-4 h-4 text-[#b91c1c] shrink-0" />
                              )}
                              <div className="flex flex-col">
                                <span className="font-medium text-[#171717]">Registration Doc</span>
                                <span className="text-[10px] text-[#7d7d7d] font-mono">
                                  {company.automated_checks.document_uploaded ? 'Uploaded' : 'None provided'}
                                </span>
                              </div>
                            </div>

                            {/* Check 3: Active Domain Conflict */}
                            <div className="flex items-center gap-2 p-2 rounded-[4px] bg-[#ffffff] border border-[#ebebeb]">
                              {!company.automated_checks.domain_conflict ? (
                                <CheckCircle2 className="w-4 h-4 text-[#15803d] shrink-0" />
                              ) : (
                                <AlertTriangle className="w-4 h-4 text-[#b91c1c] shrink-0" />
                              )}
                              <div className="flex flex-col">
                                <span className="font-medium text-[#171717]">Domain Uniqueness</span>
                                <span className="text-[10px] text-[#7d7d7d] font-mono">
                                  {company.automated_checks.domain_conflict ? 'Conflict detected' : 'Clear'}
                                </span>
                              </div>
                            </div>

                            {/* Check 4: Free Email Warning */}
                            <div className="flex items-center gap-2 p-2 rounded-[4px] bg-[#ffffff] border border-[#ebebeb]">
                              {!company.automated_checks.is_free_email ? (
                                <CheckCircle2 className="w-4 h-4 text-[#15803d] shrink-0" />
                              ) : (
                                <AlertTriangle className="w-4 h-4 text-[#b45309] shrink-0" />
                              )}
                              <div className="flex flex-col">
                                <span className="font-medium text-[#171717]">Email Provider</span>
                                <span className="text-[10px] text-[#7d7d7d] font-mono">
                                  {company.automated_checks.is_free_email ? 'Free provider (e.g. Gmail)' : 'Work domain'}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex flex-wrap lg:flex-col items-center gap-2 shrink-0">
                        {company.status === 'pending' && (
                          <>
                            <button
                              disabled={isProcessing}
                              onClick={() => handleApproveCompany(company.id, company.name)}
                              className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-[#171717] hover:bg-[#000000] text-[#ffffff] text-xs font-medium transition-colors disabled:opacity-50"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>Approve</span>
                            </button>
                            <button
                              disabled={isProcessing}
                              onClick={() => setRejectModal({ open: true, type: 'company', id: company.id, name: company.name })}
                              className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-[6px] border border-[#ebebeb] hover:bg-[#fef2f2] text-[#991b1b] text-xs font-medium transition-colors disabled:opacity-50"
                            >
                              <X className="w-3.5 h-3.5" />
                              <span>Reject</span>
                            </button>
                          </>
                        )}

                        {company.status === 'approved' && (
                          <button
                            disabled={isProcessing}
                            onClick={() => handleSuspendCompany(company.id, company.name)}
                            className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-[6px] border border-[#fca5a5] bg-[#fff5f5] text-[#b91c1c] hover:bg-[#fef2f2] text-xs font-medium transition-colors disabled:opacity-50"
                          >
                            <AlertTriangle className="w-3.5 h-3.5" />
                            <span>Suspend Company</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ===================== TAB 2: RECRUITERS ===================== */}
        {activeTab === 'recruiters' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-mono uppercase text-[#7d7d7d]">Filter:</span>
                {(['pending', 'approved', 'rejected'] as const).map((st) => (
                  <button
                    key={st}
                    onClick={() => setRecruiterStatusFilter(st)}
                    className={`px-2.5 py-1 rounded-[4px] font-mono text-xs capitalize transition-colors ${
                      recruiterStatusFilter === st
                        ? 'bg-[#171717] text-[#ffffff]'
                        : 'bg-[#ffffff] text-[#7d7d7d] border border-[#ebebeb] hover:text-[#171717]'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              <button
                onClick={fetchRecruiters}
                className="flex items-center gap-1 px-2.5 py-1 rounded-[4px] text-xs border border-[#ebebeb] bg-[#ffffff] hover:bg-[#fafafa]"
              >
                <RotateCw className="w-3 h-3" />
                <span>Refresh</span>
              </button>
            </div>

            {loadingRecruiters ? (
              <div className="py-16 text-center text-[#7d7d7d] text-sm flex flex-col items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin mb-2" />
                <span>Loading recruiter approval queue...</span>
              </div>
            ) : recruiters.length === 0 ? (
              <div className="py-16 text-center bg-[#ffffff] border border-[#ebebeb] rounded-[6px]">
                <UserCheck className="w-10 h-10 text-[#a8a8a8] mx-auto mb-2" />
                <p className="text-sm font-medium text-[#171717]">No recruiters in queue</p>
                <p className="text-xs text-[#7d7d7d] mt-1 font-mono">Status: {recruiterStatusFilter}</p>
              </div>
            ) : (
              <div className="space-y-4">
                {recruiters.map((recruiter) => (
                  <div
                    key={recruiter.user_id}
                    className="bg-[#ffffff] border border-[#ebebeb] rounded-[6px] p-5 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
                  >
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <h2 className="text-base font-bold text-[#171717]">{recruiter.full_name}</h2>
                        <StatusBadge status={recruiter.status} />
                      </div>
                      <p className="text-xs font-semibold text-[#4d4d4d]">
                        Organization: {recruiter.organization}
                      </p>
                      <div className="flex items-center gap-3 text-xs font-mono text-[#7d7d7d] mt-1">
                        <span>Email: {recruiter.email}</span>
                        <span>Domain: {recruiter.work_email_domain || 'N/A'}</span>
                        <span>Registered: {new Date(recruiter.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>

                    {recruiter.status === 'pending' && (
                      <div className="flex items-center gap-2">
                        <button
                          disabled={isProcessing}
                          onClick={() => handleApproveRecruiter(recruiter.user_id, recruiter.full_name)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-[#171717] hover:bg-[#000000] text-[#ffffff] text-xs font-medium transition-colors disabled:opacity-50"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Approve</span>
                        </button>
                        <button
                          disabled={isProcessing}
                          onClick={() => setRejectModal({ open: true, type: 'recruiter', id: recruiter.user_id, name: recruiter.full_name })}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] border border-[#ebebeb] hover:bg-[#fef2f2] text-[#991b1b] text-xs font-medium transition-colors disabled:opacity-50"
                        >
                          <X className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ===================== TAB 3: AUDIT LOG ===================== */}
        {activeTab === 'audit' && (
          <div className="bg-[#ffffff] border border-[#ebebeb] rounded-[6px] overflow-hidden shadow-sm">
            <div className="px-5 py-4 border-b border-[#ebebeb] flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-[#171717]">Administrative Audit Trail</h2>
                <p className="text-[11px] font-mono text-[#7d7d7d]">
                  Append-only immutable record of all state changes and administrative decisions
                </p>
              </div>
              <button
                onClick={fetchAuditLogs}
                className="flex items-center gap-1 px-2.5 py-1 rounded-[4px] text-xs border border-[#ebebeb] bg-[#fafafa] hover:bg-[#ebebeb]"
              >
                <RotateCw className="w-3 h-3" />
                <span>Refresh</span>
              </button>
            </div>

            {loadingAudit ? (
              <div className="py-16 text-center text-[#7d7d7d] text-sm flex flex-col items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin mb-2" />
                <span>Loading audit trail...</span>
              </div>
            ) : auditLogs.length === 0 ? (
              <div className="py-16 text-center text-[#7d7d7d] text-sm">
                No audit entries recorded yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-[#ebebeb] text-xs text-left">
                  <thead className="bg-[#fafafa] font-mono text-[#7d7d7d] uppercase text-[10px] tracking-wider">
                    <tr>
                      <th className="px-4 py-2.5">Time (UTC)</th>
                      <th className="px-4 py-2.5">Action</th>
                      <th className="px-4 py-2.5">Actor</th>
                      <th className="px-4 py-2.5">Target</th>
                      <th className="px-4 py-2.5">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#ebebeb] font-mono">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-[#fafafa] transition-colors">
                        <td className="px-4 py-2.5 text-[#7d7d7d] whitespace-nowrap">
                          {new Date(log.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-2.5 font-semibold text-[#171717]">
                          {log.action}
                        </td>
                        <td className="px-4 py-2.5 text-[#4d4d4d]">
                          {log.actor_email || 'System'}
                        </td>
                        <td className="px-4 py-2.5 text-[#7d7d7d]">
                          {log.entity_type ? `${log.entity_type} (${log.entity_id?.slice(0, 8)}...)` : '—'}
                        </td>
                        <td className="px-4 py-2.5 text-[#4d4d4d] max-w-xs truncate">
                          {log.detail ? JSON.stringify(log.detail) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Reject Modal */}
      {rejectModal && (
        <div className="fixed inset-0 z-50 bg-[#000000]/40 flex items-center justify-center p-4">
          <div className="bg-[#ffffff] rounded-[6px] border border-[#ebebeb] shadow-lg max-w-md w-full p-6">
            <h3 className="text-base font-bold text-[#171717] mb-2">
              Reject {rejectModal.type === 'company' ? 'Company' : 'Recruiter'}: {rejectModal.name}
            </h3>
            <p className="text-xs text-[#7d7d7d] mb-4">
              Please specify the reason for rejection. This reason will be recorded in the audit trail.
            </p>

            <textarea
              rows={3}
              required
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="e.g. Domain could not be verified or invalid documents."
              className="w-full px-3 py-2 text-sm bg-[#ffffff] border border-[#ebebeb] rounded-[6px] text-[#171717] placeholder:text-[#a8a8a8] focus:outline-none focus:border-[#171717] mb-4"
            />

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setRejectModal(null);
                  setRejectionReason('');
                }}
                className="px-3 py-1.5 rounded-[6px] text-xs font-medium border border-[#ebebeb] text-[#4d4d4d] hover:bg-[#fafafa]"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isProcessing || !rejectionReason.trim()}
                onClick={handleConfirmReject}
                className="px-3 py-1.5 rounded-[6px] text-xs font-medium bg-[#b91c1c] text-[#ffffff] hover:bg-[#991b1b] disabled:opacity-50"
              >
                {isProcessing ? 'Processing...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
