import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { RaxelLogo } from '../components/RaxelLogo';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Alert } from '../components/ui/Alert';
import { ArrowRight, User, Lock, Eye, EyeOff, ShieldCheck, LogIn } from 'lucide-react';
import { FadeUp, HoverLift } from '../components/motion/MotionComponents';

import { useToast } from '../context/ToastContext';

export const LoginPage = () => {
  const toast = useToast();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { user, loading: authLoading, login } = useAuth();
  const navigate = useNavigate();

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && user?.authenticated) {
      const dest = user.role === 'admin' ? '/admin' : user.role === 'faculty' ? '/faculty' : '/student';
      navigate(dest, { replace: true });
    }
  }, [user, authLoading, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await login(username.trim(), password);
      toast.success(`Welcome back, ${res?.username || username}!`);
      const dest = res?.role === 'admin' ? '/admin' : res?.role === 'faculty' ? '/faculty' : '/student';
      navigate(dest, { replace: true });
    } catch (err) {
      const errMsg = err.message || 'Invalid username or password.';
      setError(errMsg);
      toast.error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 min-h-[calc(100vh-64px)] flex flex-col items-center justify-center py-10 px-4 sm:px-6 relative overflow-hidden bg-gray-50/60 select-none">
      {/* Ambient background wash */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[400px] bg-[radial-gradient(circle,_rgba(31,27,77,0.06)_0%,_transparent_70%)] blur-[80px] pointer-events-none z-0" />

      <FadeUp className="w-full max-w-[420px] relative z-10">
        <div className="bg-white border border-raxel-border rounded-2xl shadow-lg p-7 sm:p-9 transition-all duration-300">
          
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex p-3 rounded-2xl bg-raxel-violet-soft border border-raxel-violet-muted/40 shadow-xs mb-4">
              <RaxelLogo size="md" showText={false} />
            </div>
            <h1 className="text-2xl font-bold text-raxel-indigo tracking-tight">
              Sign In to RAXEL
            </h1>
            <p className="text-xs text-raxel-muted mt-1.5 leading-relaxed">
              Enter your credentials to access your grounded campus assistant.
            </p>
          </div>

          {error && (
            <Alert type="error" message={error} onClose={() => setError('')} className="mb-5 text-xs shadow-xs" />
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="Username or ID"
              icon={User}
              placeholder="e.g. alex_student"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="text-xs"
            />

            <div className="relative">
              <Input
                label="Password"
                type={showPassword ? 'text' : 'password'}
                icon={Lock}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="text-xs"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-[34px] text-raxel-muted hover:text-raxel-indigo transition-colors p-1"
                tabIndex={-1}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>

            <Button
              type="submit"
              variant="primary"
              isLoading={loading}
              icon={LogIn}
              className="w-full mt-2 py-2.5 text-sm font-semibold rounded-xl"
            >
              {loading ? 'Signing In...' : 'Sign In'}
            </Button>
          </form>

          {/* Footer Links */}
          <div className="mt-7 pt-6 border-t border-raxel-border flex flex-col gap-3 text-center text-xs text-raxel-muted">
            <div>
              Don't have an account yet?{' '}
              <Link to="/signup" className="text-raxel-indigo font-semibold hover:underline underline-offset-2 transition-all">
                Create Account
              </Link>
            </div>

            <div className="pt-1">
              <HoverLift>
                <Link
                  to="/student"
                  className="inline-flex items-center gap-1.5 text-xs text-raxel-muted hover:text-raxel-indigo transition-colors py-1.5 px-3 rounded-lg hover:bg-raxel-surface-subtle border border-transparent hover:border-raxel-border font-medium"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-raxel-indigo" />
                  <span>Continue as Guest Student</span>
                  <ArrowRight className="w-3 h-3 ml-0.5" />
                </Link>
              </HoverLift>
            </div>
          </div>

        </div>
      </FadeUp>
    </div>
  );
};

export default LoginPage;
