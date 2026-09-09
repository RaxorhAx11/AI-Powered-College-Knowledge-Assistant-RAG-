import React from 'react';

export const Card = ({
  children,
  variant = 'default',
  className = '',
  onClick,
  ...props
}) => {
  const baseStyles = 'rounded-lg border transition-all duration-150';

  const variants = {
    default: 'bg-white border-raxel-border shadow-sm',
    glass: 'bg-white/90 backdrop-blur-md border-raxel-border shadow-sm',
    metric: 'bg-white border-raxel-border shadow-sm p-4 hover:shadow-md',
    feature: 'bg-raxel-soft-white border-raxel-border p-6',
    'teal-band': 'bg-raxel-teal-deep text-white rounded-xl p-8 sm:p-12 text-center shadow-lg',
  };

  return (
    <div
      onClick={onClick}
      className={`${baseStyles} ${variants[variant] || variants.default} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export default Card;
