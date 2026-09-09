import React, { useState } from 'react';
import { motion } from 'motion/react';
import { FileText, Cpu, Database, Sparkles, CheckCircle2, ArrowRight, Layers, ShieldCheck } from 'lucide-react';
import { ScrollBlurFocus, ScrollStaggerContainer, ScrollStaggerItem, ScrollFadeUp } from './motion/MotionComponents';

export const RagVisualization = () => {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    {
      id: 'docs',
      title: '1. Document Ingestion',
      subtitle: 'Official Regulations & PDFs',
      icon: FileText,
      badge: 'Raw Knowledge',
      desc: 'Institutional PDFs, Academic Handbooks, Examination Guidelines, and Hostel Codes are structured and parsed.',
      details: ['Academic Regulations 2025', 'Hostel Governance Rules', 'Placement Eligibility Criteria'],
      color: 'from-blue-500/10 to-indigo-500/5',
      borderColor: 'border-blue-200',
      iconColor: 'text-blue-600',
    },
    {
      id: 'vectors',
      title: '2. Vector Chunking',
      subtitle: 'FAISS Semantic Indexing',
      icon: Database,
      badge: 'Embedding Engine',
      desc: 'Texts are segmented into high-dimensional semantic vector embeddings stored in a local FAISS index.',
      details: ['Overlapping Chunking', 'Metadata Attachment', 'Section/Page Mapping'],
      color: 'from-violet-500/10 to-purple-500/5',
      borderColor: 'border-violet-200',
      iconColor: 'text-raxel-indigo',
    },
    {
      id: 'retrieval',
      title: '3. Grounded Retrieval',
      subtitle: 'Strict Context Verification',
      icon: Layers,
      badge: 'Relevance Scoring',
      desc: 'Top matched passages are retrieved via cosine similarity with threshold filters to eliminate hallucinations.',
      details: ['Similarity Score Filtering', 'Ambiguity Detection', 'Faculty Quality Control'],
      color: 'from-teal-500/10 to-emerald-500/5',
      borderColor: 'border-teal-200',
      iconColor: 'text-raxel-teal',
    },
    {
      id: 'answer',
      title: '4. RAXEL Answer',
      subtitle: 'Verifiable Answer + Citation',
      icon: Sparkles,
      badge: '100% Grounded',
      desc: 'Synthesizes concise responses backed by exact document title, section number, and page number citations.',
      details: ['Verified Citations', 'Zero Speculation', 'Instant Precision'],
      color: 'from-amber-500/10 to-raxel-violet-soft',
      borderColor: 'border-raxel-violet',
      iconColor: 'text-raxel-indigo',
    },
  ];

  return (
    <div className="w-full bg-raxel-soft-white border-t border-b border-raxel-border py-16 sm:py-20 overflow-hidden">
      <div className="rx-container">
        
        {/* Header */}
        <ScrollBlurFocus>
          <div className="text-center max-w-2xl mx-auto mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-raxel-violet-soft border border-raxel-border text-raxel-indigo text-xs font-medium uppercase tracking-wider mb-3">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>HOW RAXEL GROUNDED RAG WORKS</span>
            </div>
            <h2 className="text-2xl sm:text-4xl font-semibold text-raxel-indigo tracking-tight mb-3">
              From Official PDF to Verifiable Answer
            </h2>
            <p className="text-xs sm:text-base text-raxel-muted leading-relaxed">
              Trace how college documents are chunked, semantically indexed, and retrieved with absolute precision.
            </p>
          </div>
        </ScrollBlurFocus>

        {/* 4 Pipeline Step Cards */}
        <ScrollStaggerContainer className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 relative">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            const isSelected = activeStep === idx;

            return (
              <ScrollStaggerItem key={step.id}>
                <motion.div
                  whileHover={{ y: -4 }}
                  onClick={() => setActiveStep(idx)}
                  className={`cursor-pointer rounded-lg border p-5 transition-all duration-300 relative flex flex-col justify-between bg-white shadow-sm hover:shadow-md h-full ${
                    isSelected ? 'border-raxel-indigo ring-2 ring-raxel-indigo/10' : 'border-raxel-border'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className={`p-2.5 rounded-md bg-raxel-surface-subtle ${step.iconColor}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-raxel-surface-subtle text-raxel-muted">
                        {step.badge}
                      </span>
                    </div>

                    <h3 className="font-semibold text-sm sm:text-base text-raxel-indigo mb-0.5">
                      {step.title}
                    </h3>
                    <div className="text-xs text-raxel-muted font-medium mb-3">
                      {step.subtitle}
                    </div>

                    <p className="text-xs text-raxel-ink leading-relaxed mb-4">
                      {step.desc}
                    </p>
                  </div>

                  <div className="pt-3 border-t border-raxel-border-subtle flex flex-col gap-1.5">
                    {step.details.map((item, dIdx) => (
                      <div key={dIdx} className="text-[11px] text-raxel-muted flex items-center gap-1.5">
                        <CheckCircle2 className="w-3 h-3 text-raxel-teal shrink-0" />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              </ScrollStaggerItem>
            );
          })}
        </ScrollStaggerContainer>

        {/* Dynamic Pipeline Summary Box */}
        <ScrollFadeUp delay={0.15}>
          <div className="mt-8 bg-white border border-raxel-border rounded-lg p-5 sm:p-6 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-raxel-violet-soft flex items-center justify-center text-raxel-indigo shrink-0">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-raxel-indigo">
                  Pipeline Stage: {steps[activeStep].title}
                </div>
                <div className="text-xs text-raxel-muted mt-0.5">
                  Click any step above to inspect its document transformation workflow.
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs font-semibold text-raxel-indigo bg-raxel-surface-subtle px-4 py-2 rounded-full border border-raxel-border">
              <span>Verified Citation Guarantee</span>
              <CheckCircle2 className="w-4 h-4 text-raxel-teal" />
            </div>
          </div>
        </ScrollFadeUp>

      </div>
    </div>
  );
};

export default RagVisualization;
