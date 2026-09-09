import React from 'react';
import { Link } from 'react-router-dom';
import { RaxelLogo } from './RaxelLogo';
import { ShieldCheck, Twitter, Github, Linkedin, MessageSquare } from 'lucide-react';

export const Footer = ({ onOpenContactSales }) => {
  return (
    <footer className="bg-white border-t border-raxel-border py-12 text-raxel-muted text-sm font-normal leading-snug">
      <div className="rx-container">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 pb-12 border-b border-raxel-border-subtle">
          {/* Column 1: Brand & Social */}
          <div className="flex flex-col gap-4">
            <RaxelLogo size="sm" showText={true} />
            <p className="text-raxel-muted text-xs leading-relaxed">
              Offline-first Retrieval-Augmented Generation AI assistant for college regulations, handbooks, placements, and campus governance.
            </p>
            {/* Social Icons */}
            <div className="flex items-center gap-3 pt-1">
              <a href="#twitter" className="text-raxel-muted hover:text-raxel-indigo transition-colors" title="Twitter / X">
                <Twitter className="w-4 h-4" />
              </a>
              <a href="#github" className="text-raxel-muted hover:text-raxel-indigo transition-colors" title="GitHub">
                <Github className="w-4 h-4" />
              </a>
              <a href="#linkedin" className="text-raxel-muted hover:text-raxel-indigo transition-colors" title="LinkedIn">
                <Linkedin className="w-4 h-4" />
              </a>
              <a href="#discord" className="text-raxel-muted hover:text-raxel-indigo transition-colors" title="Discord">
                <MessageSquare className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Column 2: Navigation Links */}
          <div className="flex flex-col gap-3">
            <div className="font-semibold text-raxel-indigo text-xs uppercase tracking-wider">
              Platform Navigation
            </div>
            <Link to="/student" className="text-xs hover:text-raxel-indigo transition-colors">Chat Assistant</Link>
            <Link to="/student/sources" className="text-xs hover:text-raxel-indigo transition-colors">Knowledge Base Sources</Link>
            <Link to="/faculty" className="text-xs hover:text-raxel-indigo transition-colors">Faculty Portal</Link>
            <Link to="/admin" className="text-xs hover:text-raxel-indigo transition-colors">Admin Suite</Link>
          </div>

          {/* Column 3: RAG Architecture */}
          <div className="flex flex-col gap-3">
            <div className="font-semibold text-raxel-indigo text-xs uppercase tracking-wider">
              RAG Technology
            </div>
            <span className="text-xs">Vector Search & FAISS</span>
            <span className="text-xs">Document Citation Engine</span>
            <span className="text-xs">Multi-Tier Quality Control</span>
            <span className="text-xs">Zero Hallucinations Guarantee</span>
          </div>

          {/* Column 4: Governance & Legal */}
          <div className="flex flex-col gap-3">
            <div className="font-semibold text-raxel-indigo text-xs uppercase tracking-wider">
              Governance & Legal
            </div>
            <span className="text-xs hover:text-raxel-indigo cursor-pointer transition-colors">Privacy Policy</span>
            <span className="text-xs hover:text-raxel-indigo cursor-pointer transition-colors">Terms of Governance</span>
            <span className="text-xs hover:text-raxel-indigo cursor-pointer transition-colors">Security Audit</span>
            {onOpenContactSales && (
              <button
                onClick={onOpenContactSales}
                className="text-xs text-raxel-indigo font-semibold hover:underline text-left cursor-pointer transition-all"
              >
                Contact Sales
              </button>
            )}
          </div>
        </div>

        {/* Copyright Bottom Row */}
        <div className="pt-6 flex flex-wrap justify-between items-center gap-4 text-xs text-raxel-faint">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-raxel-teal" />
            <span>© {new Date().getFullYear()} Rx-AI Assistant. Grounded RAG Document Intelligence.</span>
          </div>
          <div className="flex gap-6">
            <span className="hover:text-raxel-muted cursor-pointer transition-colors">Privacy</span>
            <span className="hover:text-raxel-muted cursor-pointer transition-colors">Security</span>
            <span className="hover:text-raxel-muted cursor-pointer transition-colors">System Status</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
