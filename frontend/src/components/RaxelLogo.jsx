import React from 'react';

export const RaxelLogo = ({ size = 'md', showText = true, className = '' }) => {
  const sizes = {
    sm: { icon: 30, text: '1.05rem' },
    md: { icon: 36, text: '1.2rem' },
    lg: { icon: 44, text: '1.45rem' },
  };

  const s = sizes[size] || sizes.md;

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.55rem', userSelect: 'none' }} className={className}>
      {/* Minimal White Background Badge Logo */}
      <div style={{
        width: s.icon,
        height: s.icon,
        borderRadius: '8px',
        backgroundColor: '#ffffff',
        border: '1px solid #E5E7EB',
        boxShadow: '0 1px 4px rgba(17, 24, 39, 0.05)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}>
        <svg
          width={s.icon * 0.6}
          height={s.icon * 0.6}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Stylized Rx Emblem */}
          <path
            d="M 4 4 V 20 M 4 4 H 13 C 16.5 4 16.5 11 13 11 H 4 M 10 11 L 17 20"
            stroke="#1F1B4D"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="19" cy="8" r="2" fill="#1F1B4D" />
        </svg>
      </div>

      {showText && (
        <span style={{
          fontSize: s.text,
          fontWeight: 600,
          letterSpacing: '-0.035em',
          color: '#111827',
          fontFamily: "'Inter', system-ui, sans-serif",
          lineHeight: 1,
        }}>
          Rx-AI
        </span>
      )}
    </div>
  );
};

export default RaxelLogo;

