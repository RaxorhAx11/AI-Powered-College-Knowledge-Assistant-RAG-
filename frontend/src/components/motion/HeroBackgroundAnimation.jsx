import React from 'react';
import { motion } from 'motion/react';

export const HeroBackgroundAnimation = () => {
  // Sparse, elegant knowledge particles with subtle individual float paths
  const particles = [
    { id: 1, cx: '12%', cy: '25%', r: 2.5, duration: 7, delay: 0 },
    { id: 2, cx: '32%', cy: '18%', r: 2, duration: 9, delay: 1 },
    { id: 3, cx: '68%', cy: '22%', r: 2.8, duration: 8, delay: 0.5 },
    { id: 4, cx: '88%', cy: '32%', r: 2, duration: 10, delay: 1.5 },
    { id: 5, cx: '22%', cy: '72%', r: 2, duration: 8.5, delay: 2 },
    { id: 6, cx: '58%', cy: '78%', r: 2.5, duration: 7.5, delay: 0.8 },
    { id: 7, cx: '82%', cy: '68%', r: 2, duration: 9.5, delay: 1.2 },
    { id: 8, cx: '46%', cy: '38%', r: 1.8, duration: 6.5, delay: 0.3 },
  ];

  // Faint connecting vector lines representing RAG document embeddings
  const connections = [
    { x1: '12%', y1: '25%', x2: '32%', y2: '18%' },
    { x1: '32%', y1: '18%', x2: '46%', y2: '38%' },
    { x1: '68%', y1: '22%', x2: '88%', y2: '32%' },
    { x1: '58%', y1: '78%', x2: '82%', y2: '68%' },
    { x1: '22%', y1: '72%', x2: '46%', y2: '38%' },
  ];

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0 select-none">
      {/* Primary Ambient Soft Glow - Violet/Indigo Aura */}
      <motion.div
        animate={{
          scale: [1, 1.14, 1],
          opacity: [0.35, 0.52, 0.35],
          x: [0, 18, 0],
          y: [0, -15, 0],
        }}
        transition={{
          duration: 11,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="absolute -top-32 -right-12 w-[680px] h-[580px] bg-[radial-gradient(circle,_rgba(201,180,250,0.32)_0%,_rgba(139,92,246,0.18)_42%,_rgba(27,25,56,0)_70%)] blur-[90px] rounded-full"
      />

      {/* Secondary Ambient Soft Glow - Deep Cyan AI Accent */}
      <motion.div
        animate={{
          scale: [1, 1.16, 1],
          opacity: [0.2, 0.35, 0.2],
          x: [0, -22, 0],
          y: [0, 20, 0],
        }}
        transition={{
          duration: 13,
          repeat: Infinity,
          ease: 'easeInOut',
          delay: 2,
        }}
        className="absolute top-1/4 -left-24 w-[540px] h-[540px] bg-[radial-gradient(circle,_rgba(56,189,248,0.25)_0%,_rgba(99,102,241,0.14)_45%,_rgba(27,25,56,0)_70%)] blur-[100px] rounded-full"
      />

      {/* Center Top Ambient Wash - Soft Luminous Heart */}
      <motion.div
        animate={{
          opacity: [0.15, 0.28, 0.15],
          scale: [0.95, 1.08, 0.95],
        }}
        transition={{
          duration: 9,
          repeat: Infinity,
          ease: 'easeInOut',
          delay: 1,
        }}
        className="absolute top-0 left-1/3 w-[420px] h-[320px] bg-[radial-gradient(circle,_rgba(168,85,247,0.18)_0%,_rgba(27,25,56,0)_70%)] blur-[85px] rounded-full pointer-events-none"
      />

      {/* RAG Knowledge Constellation Nodes & Vector Lines (SVG) */}
      <svg className="absolute inset-0 w-full h-full opacity-35" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#c9b4fa" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.1" />
          </linearGradient>
        </defs>

        {/* Faint Connecting Lines */}
        {connections.map((line, idx) => (
          <motion.line
            key={`line-${idx}`}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="url(#lineGrad)"
            strokeWidth="1"
            strokeDasharray="4 4"
            animate={{
              strokeOpacity: [0.15, 0.5, 0.15],
            }}
            transition={{
              duration: 4.5 + idx * 0.8,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: idx * 0.5,
            }}
          />
        ))}

        {/* Floating Knowledge Nodes */}
        {particles.map((p) => (
          <g key={p.id}>
            {/* Glowing aura ring around node */}
            <motion.circle
              cx={p.cx}
              cy={p.cy}
              r={p.r * 2.6}
              fill="#c9b4fa"
              animate={{
                opacity: [0.05, 0.28, 0.05],
                scale: [0.9, 1.25, 0.9],
              }}
              transition={{
                duration: p.duration,
                repeat: Infinity,
                ease: 'easeInOut',
                delay: p.delay,
              }}
            />
            {/* Core Node Particle */}
            <motion.circle
              cx={p.cx}
              cy={p.cy}
              r={p.r}
              fill="#ffffff"
              animate={{
                opacity: [0.35, 0.9, 0.35],
                translateY: [0, -5, 0],
              }}
              transition={{
                duration: p.duration,
                repeat: Infinity,
                ease: 'easeInOut',
                delay: p.delay,
              }}
            />
          </g>
        ))}
      </svg>
    </div>
  );
};

export default HeroBackgroundAnimation;
