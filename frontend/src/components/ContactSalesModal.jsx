import React, { useState } from 'react';
import { X, Send, Sparkles, CheckCircle2, Building, Mail, User } from 'lucide-react';
import { RaxelLogo } from './RaxelLogo';
import { Button } from './ui/Button';
import { Input, Textarea } from './ui/Input';
import { Badge } from './ui/Badge';

export const ContactSalesModal = ({ isOpen, onClose }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [institution, setInstitution] = useState('');
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitting(true);
    setTimeout(() => {
      setSubmitting(false);
      setSubmitted(true);
      setTimeout(() => {
        setSubmitted(false);
        onClose();
      }, 2500);
    }, 600);
  };

  return (
    <div className="fixed inset-0 bg-raxel-indigo-deep/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg border border-raxel-border shadow-lg w-full max-w-md p-6 relative animate-fade-in">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-sm text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-surface-subtle transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {submitted ? (
          <div className="text-center py-8 px-4">
            <div className="w-13 h-13 rounded-full bg-status-success-bg text-status-success-text flex items-center justify-center mx-auto mb-4 border border-status-success-border">
              <CheckCircle2 className="w-7 h-7" />
            </div>
            <h3 className="text-xl font-semibold text-raxel-indigo mb-1">
              Inquiry Sent!
            </h3>
            <p className="text-sm text-raxel-muted">
              Thank you for reaching out. The RAXEL enterprise team will get back to you shortly.
            </p>
          </div>
        ) : (
          <>
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-2">
                <RaxelLogo size="sm" showText={true} />
                <Badge variant="student" icon={Sparkles}>
                  ENTERPRISE RAG
                </Badge>
              </div>
              <h2 className="text-xl font-semibold text-raxel-indigo tracking-tight">
                Contact Rx-AI Sales
              </h2>
              <p className="text-xs text-raxel-muted mt-1">
                Deploy grounded AI knowledge assistants across your university or college campus.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <Input
                label="Full Name"
                icon={User}
                placeholder="Dr. Alex Morgan"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />

              <Input
                label="Official Email"
                type="email"
                icon={Mail}
                placeholder="alex.morgan@university.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />

              <Input
                label="College / Institution Name"
                icon={Building}
                placeholder="GLS University"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                required
              />

              <Textarea
                label="Requirements / Message"
                placeholder="Tell us about student count or document governance needs..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={3}
              />

              <Button
                type="submit"
                variant="primary"
                isLoading={submitting}
                icon={Send}
                className="w-full mt-2"
              >
                Submit Inquiry
              </Button>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default ContactSalesModal;
