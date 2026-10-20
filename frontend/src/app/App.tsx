import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from '../lib/auth-context';
import { Navbar } from '../components/Navbar';
import { HomePage } from '../features/home/HomePage';
import { LoginPage } from '../features/auth/LoginPage';
import { RegisterPage } from '../features/auth/RegisterPage';
import { AdminApprovalQueuePage } from '../features/admin/AdminApprovalQueuePage';
import { StudentDashboardPage } from '../features/student/StudentDashboardPage';
import { CompanyDashboardPage } from '../features/company/CompanyDashboardPage';
import { RecruiterDashboardPage } from '../features/recruiter/RecruiterDashboardPage';
import { PublicVerificationPage } from '../features/verification/PublicVerificationPage';

const ProtectedRoute: React.FC<{
  children: React.ReactNode;
  allowedRoles?: Array<'student' | 'company' | 'recruiter' | 'admin'>;
}> = ({ children, allowedRoles }) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <span className="font-mono text-xs text-[#7d7d7d] animate-pulse">Loading session...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // If admin, allow viewing any role view for platform governance
    if (user.role === 'admin') {
      return <>{children}</>;
    }
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="min-h-screen bg-[#fafafa] flex flex-col font-sans text-[#171717]">
          <Navbar />
          <main className="flex-1">
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/verify" element={<PublicVerificationPage />} />
              <Route path="/verify/:id" element={<PublicVerificationPage />} />

              {/* Admin Routes */}
              <Route
                path="/admin"
                element={<Navigate to="/admin/approvals" replace />}
              />
              <Route
                path="/admin/approvals"
                element={
                  <ProtectedRoute allowedRoles={['admin']}>
                    <AdminApprovalQueuePage defaultTab="companies" />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/audit"
                element={
                  <ProtectedRoute allowedRoles={['admin']}>
                    <AdminApprovalQueuePage defaultTab="audit" />
                  </ProtectedRoute>
                }
              />

              {/* Role Dashboards */}
              <Route
                path="/student"
                element={
                  <ProtectedRoute allowedRoles={['student']}>
                    <StudentDashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/company"
                element={
                  <ProtectedRoute allowedRoles={['company']}>
                    <CompanyDashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/recruiter"
                element={
                  <ProtectedRoute allowedRoles={['recruiter']}>
                    <RecruiterDashboardPage />
                  </ProtectedRoute>
                }
              />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
