import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Alert } from '../components/ui/Alert';
import { ShieldCheck, User, Lock, Eye, EyeOff, Sparkles, UserPlus, CheckCircle2 } from 'lucide-react';
import { FadeUp } from '../components/motion/MotionComponents';

import { useToast } from '../context/ToastContext';

export const SignupPage = () => {
  const toast = useToast();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { user, loading: authLoading, signup } = useAuth();
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

    if (password !== confirmPassword) {
      const msg = 'Passwords do not match. Please re-enter your password.';
      setError(msg);
      toast.error(msg);
      return;
    }

    if (password.length < 4) {
      const msg = 'Password must be at least 4 characters long.';
      setError(msg);
      toast.error(msg);
      return;
    }

    setLoading(true);
    try {
      await signup(username.trim(), password, 'student');
      toast.success('Account created successfully! Welcome to RAXEL.');
      navigate('/student', { replace: true });
    } catch (err) {
      const errMsg = err.message || 'Registration failed. Username may already exist.';
      setError(errMsg);
      toast.error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 min-h-[calc(100vh-64px)] flex flex-col items-center justify-center py-10 px-4 sm:px-6 relative overflow-hidden bg-gray-50/60 select-none">
      {/* Ambient background accent */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[450px] bg-[radial-gradient(circle,_rgba(31,27,77,0.05)_0%,_transparent_70%)] blur-[80px] pointer-events-none z-0" />

      <FadeUp className="w-full max-w-[440px] relative z-10">
        <div className="bg-white border border-raxel-border rounded-2xl shadow-lg p-7 sm:p-9 transition-all duration-300">
          
          {/* Header */}
          <div className="text-center mb-6">
            <div className="inline-flex p-3 rounded-2xl bg-raxel-violet-soft border border-raxel-violet-muted/40 shadow-xs mb-4">
              <UserPlus className="w-6 h-6 text-raxel-indigo" />
            </div>
            <h1 className="text-2xl font-bold text-raxel-indigo tracking-tight">
              Create Student Account
            </h1>
            <p className="text-xs text-raxel-muted mt-1.5 leading-relaxed">
              Register now to start asking grounded questions about your college regulations.
            </p>
          </div>

          {error && (
            <Alert type="error" message={error} onClose={() => setError('')} className="mb-5 text-xs shadow-xs" />
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            
            {/* Role Info Box */}
            <div className="p-3 bg-raxel-surface-subtle border border-raxel-border rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-raxel-indigo" />
                <span className="text-xs font-semibold text-raxel-indigo">Assigned Access</span>
              </div>
              <Badge variant="student" icon={Sparkles}>
                Student Portal
              </Badge>
            </div>

            <Input
              label="Username"
              icon={User}
              placeholder="Choose a username (e.g. alex_student)"
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
                placeholder="Choose a password"
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

            <Input
              label="Confirm Password"
              type={showPassword ? 'text' : 'password'}
              icon={Lock}
              placeholder="Re-enter your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="text-xs"
            />

            <Button
              type="submit"
              variant="primary"
              isLoading={loading}
              icon={CheckCircle2}
              className="w-full mt-2 py-2.5 text-sm font-semibold rounded-xl"
            >
              {loading ? 'Creating Account...' : 'Complete Registration'}
            </Button>
          </form>

          {/* Footer Link */}
          <div className="mt-7 pt-6 border-t border-raxel-border text-center text-xs text-raxel-muted">
            Already have an account?{' '}
            <Link to="/login" className="text-raxel-indigo font-semibold hover:underline underline-offset-2 transition-all">
              Sign In
            </Link>
          </div>

        </div>
      </FadeUp>
    </div>
  );
};

export default SignupPage;
