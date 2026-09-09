import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { ArrowRight, LogIn, ShieldCheck, Search, BookOpen, Sparkles, CheckCircle2, FileCheck2, Cpu } from 'lucide-react';
import { RaxelLogo } from '../components/RaxelLogo';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { RagVisualization } from '../components/RagVisualization';
import { FadeUp, ScaleIn, HoverLift, ScrollBlurFocus, ScrollSlideLeft, ScrollSlideRight, ScrollFadeUp } from '../components/motion/MotionComponents';
import { HeroBackgroundAnimation } from '../components/motion/HeroBackgroundAnimation';

export const LandingPage = () => {
  const navigate = useNavigate();

  const heroChatExamples = [
    {
      question: "What is the minimum attendance requirement?",
      answer: "Students must maintain a minimum of ",
      highlight: "75% attendance",
      answerSuffix: " in each registered course to be eligible for semester end examinations as mandated in Section 4.2.",
      docTitle: "Academic Regulations Handbook 2025",
      docMeta: "Section 4.2 · Attendance Policy · Page 14"
    },
    {
      question: "What are the eligibility criteria for campus placements?",
      answer: "Candidates must possess a minimum ",
      highlight: "CGPA of 6.5 with zero active backlogs",
      answerSuffix: " at the time of company registration as outlined in Placement Policy Clause 3.1.",
      docTitle: "Training & Placement Governance Code",
      docMeta: "Clause 3.1 · Campus Drives Eligibility · Page 8"
    },
    {
      question: "How do I apply for answer script re-evaluation?",
      answer: "Re-evaluation applications must be submitted ",
      highlight: "within 10 days of result publication",
      answerSuffix: " via the student portal along with the prescribed fee of ₹500 per subject.",
      docTitle: "Controller of Examinations Guidelines",
      docMeta: "Section 7.4 · Re-evaluation Rules · Page 22"
    },
    {
      question: "What is the weekend hostel curfew time for resident students?",
      answer: "Resident students must report to their respective hostels by ",
      highlight: "8:30 PM on weekends",
      answerSuffix: ". Outing passes must be approved by the warden 24 hours in advance.",
      docTitle: "Hostel Resident Rules & Code of Conduct",
      docMeta: "Section 2.3 · Campus Timings & Curfew · Page 5"
    }
  ];

  const [activeChatIndex, setActiveChatIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveChatIndex((prev) => (prev + 1) % heroChatExamples.length);
    }, 6000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex flex-col w-full min-h-0">

      {/* CANVAS 1: EDITORIAL DARK HERO (Indigo Navy #1b1938 with Violet Glow) */}
      <section className="bg-[#1b1938] text-white relative overflow-hidden py-16 sm:py-24 lg:py-28">
        {/* Soft animated ambient background wash & knowledge nodes */}
        <HeroBackgroundAnimation />

        {/* Hero Content Container - Fully Visible & Un-clipped */}
        <div className="rx-container relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">

          {/* Left Hero Column */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            <FadeUp delay={0.05}>
              <div className="inline-flex items-center gap-2 w-fit">
                <Sparkles className="w-4 h-4 text-[#B29DF8] shrink-0 animate-pulse" />
                <span className="text-xs sm:text-sm font-bold tracking-wider text-[#B29DF8] uppercase drop-shadow-[0_0_12px_rgba(178,157,248,0.4)]">
                  RAXEL ASSISTANT
                </span>
              </div>
            </FadeUp>

            <FadeUp delay={0.12}>
              <h1 className="text-3xl sm:text-5xl lg:text-6xl font-semibold text-white tracking-tight leading-[1.15]">
                Your college knowledge.<br />
                <span className="text-[#B29DF8]">One clear answer.</span>
              </h1>
            </FadeUp>

            <FadeUp delay={0.18}>
              <p className="text-sm sm:text-base lg:text-lg font-normal text-[#94A3B8] leading-relaxed max-w-xl">
                Ask RAXEL about academic regulations, attendance criteria, exam deadlines, hostel rules, placements, and governance policies with verified document citations.
              </p>
            </FadeUp>

            {/* Hero Action Buttons */}
            <FadeUp delay={0.25}>
              <div className="flex flex-wrap items-center gap-4 pt-2">
                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Button
                    variant="on-dark-pill"
                    size="lg"
                    onClick={() => navigate('/student')}
                    icon={ArrowRight}
                  >
                    Continue as Student
                  </Button>
                </motion.div>

                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Button
                    variant="secondary"
                    size="lg"
                    icon={LogIn}
                    onClick={() => navigate('/login')}
                  >
                    Sign In
                  </Button>
                </motion.div>
              </div>
            </FadeUp>
          </div>

          {/* Right Hero Visual Card - Fixed & Completely Stable */}
          <div className="lg:col-span-5 flex justify-center lg:justify-end">
            <ScaleIn delay={0.2}>
              <div className="w-full max-w-md relative select-none">
                {/* Subtle, soft ambient highlight backlight aura (static backdrop) */}
                <div className="absolute -inset-2 bg-gradient-to-r from-purple-500/25 via-indigo-500/20 to-sky-400/25 rounded-2xl blur-xl pointer-events-none" />

                {/* Completely Stable & Fixed Card - No floating, shaking, or moving */}
                <div className="relative z-10 bg-white text-raxel-ink rounded-lg border border-raxel-border p-6 shadow-xl flex flex-col gap-4 min-h-[350px]">
                  {/* Card Top Header */}
                  <div className="flex justify-between items-center">
                    <RaxelLogo size="sm" showText={true} />
                    <Badge
                      variant="indexed"
                      icon={() => (
                        <span className="relative flex h-2 w-2 shrink-0">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
                        </span>
                      )}
                    >
                      Grounded RAG
                    </Badge>
                  </div>

                  {/* Animated Chat Content (Blur + Fade Transition) */}
                  <div className="relative flex-1 flex flex-col justify-between min-h-[220px]">
                    <AnimatePresence mode="wait">
                      <motion.div
                        key={activeChatIndex}
                        initial={{ opacity: 0, filter: 'blur(14px)', y: 6 }}
                        animate={{ opacity: 1, filter: 'blur(0px)', y: 0 }}
                        exit={{ opacity: 0, filter: 'blur(14px)', y: -6 }}
                        transition={{ duration: 0.95, ease: [0.22, 1, 0.36, 1] }}
                        className="flex flex-col gap-3"
                      >
                        <div className="bg-raxel-violet-soft p-3.5 rounded-sm text-xs sm:text-sm font-semibold text-raxel-indigo">
                          {heroChatExamples[activeChatIndex].question}
                        </div>

                        <div className="text-xs sm:text-sm text-raxel-ink leading-relaxed">
                          {heroChatExamples[activeChatIndex].answer}
                          <strong className="font-semibold text-raxel-indigo">
                            {heroChatExamples[activeChatIndex].highlight}
                          </strong>
                          {heroChatExamples[activeChatIndex].answerSuffix}
                        </div>

                        <div className="bg-raxel-soft-white border border-raxel-border rounded-sm p-3 text-xs flex flex-col gap-1 mt-1">
                          <div className="font-semibold text-raxel-teal-deep flex items-center gap-1.5">
                            <BookOpen className="w-3.5 h-3.5 text-raxel-teal shrink-0" />
                            {heroChatExamples[activeChatIndex].docTitle}
                          </div>
                          <div className="text-raxel-muted text-[11px]">
                            {heroChatExamples[activeChatIndex].docMeta}
                          </div>
                        </div>
                      </motion.div>
                    </AnimatePresence>

                    {/* Navigation Dots Indicator */}
                    <div className="flex justify-center items-center gap-1.5 pt-3 mt-3 border-t border-raxel-border/50">
                      {heroChatExamples.map((_, idx) => (
                        <button
                          key={idx}
                          onClick={() => setActiveChatIndex(idx)}
                          className={`h-1.5 rounded-full transition-all duration-300 focus:outline-none ${idx === activeChatIndex
                              ? 'w-6 bg-raxel-indigo'
                              : 'w-1.5 bg-raxel-border hover:bg-raxel-muted'
                            }`}
                          aria-label={`View chatbot example ${idx + 1}`}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </ScaleIn>
          </div>

        </div>
      </section>

      {/* CANVAS 2: 2D KNOWLEDGE RAG VISUALIZATION */}
      <RagVisualization />

      {/* CANVAS 3: WHITE BODY (Verified Knowledge Architecture) */}
      <section className="bg-white py-16 sm:py-24 border-b border-raxel-border overflow-hidden">
        <div className="rx-container">

          <ScrollBlurFocus>
            <div className="text-center mb-12 sm:mb-16 max-w-2xl mx-auto">
              <h2 className="text-2xl sm:text-3xl font-semibold text-raxel-indigo tracking-tight mb-3">
                Verified Knowledge Architecture
              </h2>
              <p className="text-xs sm:text-base text-raxel-muted">
                Built strictly on official institutional documents with administrative governance controls.
              </p>
            </div>
          </ScrollBlurFocus>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
            <ScrollSlideLeft delay={0.05}>
              <HoverLift className="h-full">
                <Card variant="feature" className="flex flex-col gap-4 h-full">
                  <div className="w-11 h-11 rounded-md bg-raxel-teal-light flex items-center justify-center text-raxel-teal">
                    <Search className="w-5.5 h-5.5" />
                  </div>
                  <h3 className="text-base sm:text-lg font-semibold text-raxel-indigo">
                    Grounded Vector RAG
                  </h3>
                  <p className="text-xs sm:text-sm text-raxel-ink leading-relaxed">
                    Questions are answered using FAISS semantic vector search over chunked official college PDFs.
                  </p>
                </Card>
              </HoverLift>
            </ScrollSlideLeft>

            <ScrollFadeUp delay={0.12}>
              <HoverLift className="h-full">
                <Card variant="feature" className="flex flex-col gap-4 h-full">
                  <div className="w-11 h-11 rounded-md bg-raxel-violet-soft flex items-center justify-center text-raxel-indigo">
                    <BookOpen className="w-5.5 h-5.5" />
                  </div>
                  <h3 className="text-base sm:text-lg font-semibold text-raxel-indigo">
                    Verifiable Citations
                  </h3>
                  <p className="text-xs sm:text-sm text-raxel-ink leading-relaxed">
                    Every synthesized answer includes exact document metadata, section headers, page numbers, and version stamps.
                  </p>
                </Card>
              </HoverLift>
            </ScrollFadeUp>

            <ScrollSlideRight delay={0.18}>
              <HoverLift className="h-full">
                <Card variant="feature" className="flex flex-col gap-4 h-full">
                  <div className="w-11 h-11 rounded-md bg-raxel-surface-subtle flex items-center justify-center text-raxel-indigo">
                    <ShieldCheck className="w-5.5 h-5.5" />
                  </div>
                  <h3 className="text-base sm:text-lg font-semibold text-raxel-indigo">
                    Faculty & Admin Quality Control
                  </h3>
                  <p className="text-xs sm:text-sm text-raxel-ink leading-relaxed">
                    Multi-tier approval workflows with metadata verification and system health diagnostics.
                  </p>
                </Card>
              </HoverLift>
            </ScrollSlideRight>
          </div>

          {/* Supported Knowledge Domains */}
          <ScrollFadeUp delay={0.15}>
            <div className="mt-14 sm:mt-16 text-center">
              <div className="text-xs font-bold uppercase text-raxel-muted tracking-wider mb-4">
                Supported Knowledge Domains
              </div>
              <div className="flex flex-wrap gap-2 justify-center">
                {['Academic Regulations', 'Examination Deadlines', 'Hostel Governance', 'Placement Rules', 'Fee Structure', 'Curriculum Syllabus', 'Disciplinary Code'].map((domain, i) => (
                  <button
                    key={i}
                    className="bg-white text-raxel-ink rounded-full px-4 py-2 text-xs font-semibold border border-raxel-border hover:border-raxel-indigo hover:text-raxel-indigo transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo"
                  >
                    {domain}
                  </button>
                ))}
              </div>
            </div>
          </ScrollFadeUp>

        </div>
      </section>

      {/* CANVAS 4: SIGNATURE CLOSING TEAL BAND (#0e3030) */}
      <section className="py-14 sm:py-20 bg-raxel-soft-white overflow-hidden">
        <div className="rx-container">
          <ScrollBlurFocus delay={0.05}>
            <Card variant="teal-band" className="flex flex-col items-center text-center">
              <h2 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight mb-4 max-w-xl">
                Ready to explore verified college answers?
              </h2>
              <p className="text-xs sm:text-base text-[#b2d8d8] max-w-lg mb-8 leading-relaxed">
                Access instant, grounded information directly sourced from official regulations and guidelines.
              </p>
              <Button
                variant="on-teal"
                size="lg"
                onClick={() => navigate('/student')}
                icon={ArrowRight}
              >
                Launch Student Assistant
              </Button>
            </Card>
          </ScrollBlurFocus>
        </div>
      </section>

    </div>
  );
};

export default LandingPage;
