import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'motion/react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { GlobalLayout } from './components/GlobalLayout';
import { PageTransition } from './components/motion/MotionComponents';
import { PageSkeletonFallback } from './components/ui/PageSkeletonFallback';

import LandingPage from './pages/LandingPage';
import StudentPage from './pages/StudentPage';

const SourcesPage = React.lazy(() => import('./pages/SourcesPage'));
const FacultyPage = React.lazy(() => import('./pages/FacultyPage'));
const AdminPage = React.lazy(() => import('./pages/AdminPage'));
const LoginPage = React.lazy(() => import('./pages/LoginPage'));
const SignupPage = React.lazy(() => import('./pages/SignupPage'));

const PageFallback = () => <PageSkeletonFallback />;

function ScrollToTop() {
  const { pathname } = useLocation();

  React.useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }, [pathname]);

  return null;
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Uncaught error in UI component:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-raxel-surface-subtle text-center">
          <h2 className="text-xl font-bold text-raxel-indigo mb-2">Something went wrong</h2>
          <p className="text-xs text-raxel-muted mb-4">{this.state.error?.message || 'An unexpected rendering error occurred.'}</p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.href = '/';
            }}
            className="px-4 py-2 text-xs font-semibold text-white bg-raxel-indigo rounded-md hover:bg-raxel-indigo-deep"
          >
            Return to Home
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const ProtectedRoute = ({ children, requiredRole }) => {
  const { user, loading } = useAuth();
  if (loading) return <PageFallback />;

  if (!user?.authenticated) {
    return <Navigate to="/login" replace />;
  }

  const roleLevels = { student: 1, faculty: 2, admin: 3 };
  const userLevel = roleLevels[user.role] || 1;
  const requiredLevel = roleLevels[requiredRole] || 1;

  if (userLevel < requiredLevel) {
    return <Navigate to="/student" replace />;
  }

  return children;
};

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageTransition><LandingPage /></PageTransition>} />
        <Route path="/login" element={<PageTransition><LoginPage /></PageTransition>} />
        <Route path="/signup" element={<PageTransition><SignupPage /></PageTransition>} />
        <Route path="/student" element={<PageTransition className="h-full flex flex-col flex-1"><StudentPage /></PageTransition>} />
        <Route path="/student/sources" element={<PageTransition><SourcesPage /></PageTransition>} />

        {/* Faculty Routes */}
        <Route
          path="/faculty"
          element={
            <ProtectedRoute requiredRole="faculty">
              <PageTransition><FacultyPage /></PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/faculty/upload"
          element={
            <ProtectedRoute requiredRole="faculty">
              <PageTransition><FacultyPage isUploadModalOpenDefault={true} /></PageTransition>
            </ProtectedRoute>
          }
        />

        {/* Admin Routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="admin">
              <PageTransition><AdminPage activeTab="overview" /></PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/approvals"
          element={
            <ProtectedRoute requiredRole="admin">
              <PageTransition><AdminPage activeTab="approvals" /></PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute requiredRole="admin">
              <PageTransition><AdminPage activeTab="users" /></PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/quality"
          element={
            <ProtectedRoute requiredRole="admin">
              <PageTransition><AdminPage activeTab="quality" /></PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/recovery"
          element={
            <ProtectedRoute requiredRole="admin">
              <PageTransition><AdminPage activeTab="recovery" /></PageTransition>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/diagnostics"
          element={
            <ProtectedRoute requiredRole="admin">
              <PageTransition><AdminPage activeTab="diagnostics" /></PageTransition>
            </ProtectedRoute>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ScrollToTop />
        <AuthProvider>
          <ToastProvider>
            <GlobalLayout>
              <AnimatedRoutes />
            </GlobalLayout>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
