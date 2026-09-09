import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Sparkles, FileSearch } from 'lucide-react';

const SEARCH_PHASES = [
  { text: "RAXEL is searching verified knowledge", sub: "Searching semantic vector index..." },
  { text: "RAXEL is searching verified knowledge", sub: "Retrieving grounded document passages..." },
  { text: "RAXEL is searching verified knowledge", sub: "Verifying official handbook citations..." }
];

export const RaxelSearchAnimation = () => {
  const [phaseIndex, setPhaseIndex] = useState(0);

  // Cycle sub-phase messages smoothly
  useEffect(() => {
    const interval = setInterval(() => {
      setPhaseIndex((prev) => (prev + 1) % SEARCH_PHASES.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const currentPhase = SEARCH_PHASES[phaseIndex];

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="self-start my-2 max-w-md w-auto"
    >
      {/* Sleek Minimalist Transparent Card */}
      <div className="bg-white/95 backdrop-blur-md rounded-xl px-4 py-3 border border-raxel-border shadow-xs flex items-center gap-3.5 relative overflow-hidden">
        
        {/* Minimalist Vector Node Indicator */}
        <div className="relative shrink-0 w-9 h-9 rounded-lg bg-raxel-violet-soft/80 border border-raxel-violet-muted/60 flex items-center justify-center overflow-hidden">
          {/* Subtle concentric wave pulse */}
          <motion.div
            animate={{ scale: [0.85, 1.25], opacity: [0.5, 0] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
            className="absolute inset-0 rounded-lg bg-raxel-indigo/15 pointer-events-none"
          />
          {/* Minimalist central AI spark */}
          <Sparkles className="w-4 h-4 text-raxel-indigo relative z-10" />
        </div>

        {/* Text & Status */}
        <div className="flex-1 min-w-0 flex flex-col justify-center">
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-xs sm:text-sm font-semibold text-raxel-indigo tracking-tight">
              {currentPhase.text}
            </h4>
            {/* Minimalist hairline pulsing progress indicator */}
            <div className="w-10 h-1 bg-raxel-violet-soft rounded-full overflow-hidden shrink-0 relative">
              <motion.div
                animate={{ x: ['-100%', '100%'] }}
                transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
                className="w-1/2 h-full bg-raxel-indigo rounded-full"
              />
            </div>
          </div>

          <div className="h-4 relative overflow-hidden mt-0.5">
            <AnimatePresence mode="wait">
              <motion.p
                key={phaseIndex}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.2 }}
                className="text-[11px] text-raxel-muted truncate flex items-center gap-1.5 absolute inset-0"
              >
                <FileSearch className="w-3.5 h-3.5 text-raxel-indigo/70 shrink-0" />
                <span>{currentPhase.sub}</span>
              </motion.p>
            </AnimatePresence>
          </div>
        </div>

      </div>
    </motion.div>
  );
};

export default RaxelSearchAnimation;

