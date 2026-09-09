import React from 'react';
import { motion } from 'motion/react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  icon: Icon = null,
  type = 'button',
  className = '',
  onClick,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-md transition-colors duration-150 select-none whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none';

  const variants = {
    primary: 'bg-raxel-indigo text-white shadow-sm hover:bg-raxel-indigo-deep hover:shadow-md',
    secondary: 'bg-white text-raxel-ink border border-raxel-border hover:bg-raxel-surface-hover hover:text-raxel-indigo',
    ghost: 'bg-transparent text-raxel-muted hover:bg-raxel-surface-hover hover:text-raxel-indigo',
    teal: 'bg-raxel-indigo text-white shadow-sm hover:bg-raxel-indigo-deep',
    danger: 'bg-status-danger-bg text-status-danger-text border border-status-danger-border hover:bg-[#FEE2E2]',
    'on-dark-pill': 'bg-white text-raxel-indigo font-medium rounded-full hover:bg-raxel-surface-hover shadow-sm',
    'on-teal': 'bg-white text-raxel-indigo font-medium rounded-md hover:bg-raxel-surface-hover hover:shadow-md',
  };

  const sizes = {
    sm: 'text-xs px-3 py-1.5 min-h-[32px] gap-1.5',
    md: 'text-sm px-4 py-2 min-h-[38px] gap-2',
    lg: 'text-base px-5 py-2.5 min-h-[44px] gap-2.5',
  };

  return (
    <motion.button
      whileTap={{ scale: disabled || isLoading ? 1 : 0.98 }}
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={cn(baseStyles, variants[variant] || variants.primary, sizes[size] || sizes.md, className)}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin shrink-0" />
      ) : Icon ? (
        <Icon className="w-4 h-4 shrink-0" />
      ) : null}
      <span>{children}</span>
    </motion.button>
  );
};

export default Button;
