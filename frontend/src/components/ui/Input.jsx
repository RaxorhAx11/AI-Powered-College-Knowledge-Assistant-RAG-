import React, { forwardRef } from 'react';

export const Input = forwardRef(({
  label,
  error,
  helperText,
  icon: Icon,
  type = 'text',
  className = '',
  id,
  required,
  ...props
}, ref) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label htmlFor={inputId} className="text-xs font-medium text-raxel-ink flex items-center justify-between">
          <span>
            {label} {required && <span className="text-status-danger-text">*</span>}
          </span>
        </label>
      )}
      <div className="relative flex items-center w-full">
        {Icon && (
          <div className="absolute left-3 text-raxel-muted pointer-events-none flex items-center justify-center">
            <Icon className="w-4 h-4" />
          </div>
        )}
        <input
          ref={ref}
          id={inputId}
          type={type}
          required={required}
          className={`w-full bg-white text-raxel-ink text-sm px-3.5 py-2.5 rounded-sm border border-raxel-border transition-all duration-150 outline-none min-h-[42px] focus:border-raxel-indigo focus:ring-2 focus:ring-raxel-indigo/10 disabled:bg-raxel-surface-subtle disabled:text-raxel-muted disabled:cursor-not-allowed ${Icon ? 'pl-9' : ''} ${error ? 'border-status-danger-border focus:border-status-danger-text focus:ring-status-danger-border/30' : ''} ${className}`}
          {...props}
        />
      </div>
      {error ? (
        <span className="text-xs text-status-danger-text font-medium">{error}</span>
      ) : helperText ? (
        <span className="text-xs text-raxel-muted">{helperText}</span>
      ) : null}
    </div>
  );
});

Input.displayName = 'Input';

export const Select = forwardRef(({
  label,
  error,
  children,
  className = '',
  id,
  required,
  ...props
}, ref) => {
  const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label htmlFor={selectId} className="text-xs font-medium text-raxel-ink">
          {label} {required && <span className="text-status-danger-text">*</span>}
        </label>
      )}
      <select
        ref={ref}
        id={selectId}
        required={required}
        className={`w-full bg-white text-raxel-ink text-sm px-3.5 py-2.5 rounded-sm border border-raxel-border transition-all duration-150 outline-none min-h-[42px] focus:border-raxel-indigo focus:ring-2 focus:ring-raxel-indigo/10 disabled:bg-raxel-surface-subtle disabled:cursor-not-allowed ${error ? 'border-status-danger-border' : ''} ${className}`}
        {...props}
      >
        {children}
      </select>
      {error && <span className="text-xs text-status-danger-text font-medium">{error}</span>}
    </div>
  );
});

Select.displayName = 'Select';

export const Textarea = forwardRef(({
  label,
  error,
  helperText,
  rows = 3,
  className = '',
  id,
  required,
  ...props
}, ref) => {
  const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label htmlFor={textareaId} className="text-xs font-medium text-raxel-ink">
          {label} {required && <span className="text-status-danger-text">*</span>}
        </label>
      )}
      <textarea
        ref={ref}
        id={textareaId}
        rows={rows}
        required={required}
        className={`w-full bg-white text-raxel-ink text-sm px-3.5 py-2.5 rounded-sm border border-raxel-border transition-all duration-150 outline-none focus:border-raxel-indigo focus:ring-2 focus:ring-raxel-indigo/10 disabled:bg-raxel-surface-subtle disabled:cursor-not-allowed ${error ? 'border-status-danger-border' : ''} ${className}`}
        {...props}
      />
      {error ? (
        <span className="text-xs text-status-danger-text font-medium">{error}</span>
      ) : helperText ? (
        <span className="text-xs text-raxel-muted">{helperText}</span>
      ) : null}
    </div>
  );
});

Textarea.displayName = 'Textarea';
