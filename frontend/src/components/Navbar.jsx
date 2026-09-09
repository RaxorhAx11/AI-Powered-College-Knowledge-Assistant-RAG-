import React, { useState, useMemo } from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { useAuth } from '../context/AuthContext';
import { RaxelLogo } from './RaxelLogo';
import { Button } from './ui/Button';
import { LogOut, LogIn, Menu, X, Sparkles, MessageSquare, BookOpen, Shield, Users } from 'lucide-react';

export const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [hoveredPath, setHoveredPath] = useState(null);

  const role = user?.role || 'student';
  const isAuth = user?.authenticated;
  const isAuthRoute = location.pathname === '/login' || location.pathname === '/signup';

  const handleLogout = async () => {
    await logout();
    setMobileMenuOpen(false);
    navigate('/login');
  };

  const navLinks = useMemo(() => {
    const links = [
      { path: '/student', label: 'Chat', icon: MessageSquare },
      { path: '/student/sources', label: 'Sources', icon: BookOpen },
    ];

    if ((role === 'faculty' || role === 'admin') && isAuth) {
      links.push({ path: '/faculty', label: 'Faculty', icon: Shield });
    }

    if (role === 'admin' && isAuth) {
      links.push({ path: '/admin', label: 'Admin', icon: Users });
    }

    return links;
  }, [role, isAuth]);

  if (isAuthRoute) {
    return (
      <header className="glass-header sticky top-0 z-50 h-16 flex items-center w-full select-none border-b border-raxel-border/60">
        <div className="rx-container flex items-center justify-between gap-4 h-full">
          <Link
            to="/"
            className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo rounded-md p-1 transition-opacity hover:opacity-90"
          >
            <RaxelLogo size="sm" showText={true} />
          </Link>
          <Link
            to="/"
            className="text-xs font-semibold text-raxel-muted hover:text-raxel-indigo transition-colors flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-raxel-border/60 hover:border-raxel-indigo/40 bg-white/80 shadow-2xs"
          >
            <span>Back to Home</span>
          </Link>
        </div>
      </header>
    );
  }

  return (
    <header className="glass-header sticky top-0 z-50 h-16 flex items-center w-full select-none">
      <div className="rx-container flex items-center justify-between gap-4 h-full">

        {/* LEFT SECTION: Brand Logo & Desktop Navigation */}
        <div className="flex items-center gap-6 sm:gap-8 shrink-0">
          <Link
            to="/"
            className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo rounded-md p-1 transition-opacity hover:opacity-90"
          >
            <RaxelLogo size="sm" showText={true} />
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path;
              const isHovered = hoveredPath === link.path;

              return (
                <NavLink
                  key={link.path}
                  to={link.path}
                  onMouseEnter={() => setHoveredPath(link.path)}
                  onMouseLeave={() => setHoveredPath(null)}
                  className={`relative px-3 py-1.5 text-sm font-medium transition-colors duration-200 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo ${isActive
                      ? 'text-raxel-indigo font-semibold'
                      : 'text-raxel-muted hover:text-raxel-indigo'
                    }`}
                >
                  <span className="relative z-10 flex items-center gap-1.5">
                    {link.label}
                  </span>

                  {/* Persistent Active Route Underline (Animates Left to Right) */}
                  {isActive && (
                    <motion.div
                      layoutId="activeUnderline"
                      className="absolute bottom-0 left-3 right-3 h-[2px] bg-raxel-indigo rounded-full"
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      style={{ originX: 0 }}
                      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
                    />
                  )}

                  {/* Hover State Underline (Left to Right expand when hovered & not active) */}
                  {!isActive && isHovered && (
                    <motion.div
                      className="absolute bottom-0 left-3 right-3 h-[2px] bg-raxel-indigo/40 rounded-full"
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      exit={{ scaleX: 0 }}
                      style={{ originX: 0 }}
                      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                    />
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* RIGHT SECTION: Auth Actions */}
        <div className="flex items-center gap-3 shrink-0">
          {isAuth ? (
            <Button
              variant="secondary"
              size="sm"
              icon={LogOut}
              onClick={handleLogout}
            >
              Sign Out
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              icon={LogIn}
              onClick={() => navigate('/login')}
            >
              Sign In
            </Button>
          )}

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-md text-raxel-indigo hover:bg-raxel-surface-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo transition-colors"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* MOBILE NAVIGATION DRAWER */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="md:hidden absolute top-16 left-0 right-0 bg-white border-b border-raxel-border shadow-lg p-4 flex flex-col gap-1.5 z-40"
          >
            {navLinks.map((link) => (
              <NavLink
                key={link.path}
                to={link.path}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `px-4 py-2.5 rounded-md text-sm font-medium flex items-center gap-2 transition-all ${isActive
                    ? 'bg-raxel-violet-soft text-raxel-indigo font-semibold'
                    : 'text-raxel-muted hover:bg-raxel-surface-subtle hover:text-raxel-indigo'
                  }`
                }
              >
                <span>{link.label}</span>
              </NavLink>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};

export default Navbar;
