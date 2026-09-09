import React from 'react';
import { motion } from 'motion/react';

// Reusable transition presets for smooth 2D SaaS motion
const transitionDefaults = {
  duration: 0.25,
  ease: [0.16, 1, 0.3, 1], // Custom smooth ease-out
};

const pageTransitionDefaults = {
  duration: 0.18,
  ease: [0.16, 1, 0.3, 1],
};

export const PageTransition = ({ children, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, y: 4 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -4 }}
    transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
    className={className}
  >
    {children}
  </motion.div>
);

export const FadeIn = ({ children, delay = 0, className = '' }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ ...transitionDefaults, delay }}
    className={className}
  >
    {children}
  </motion.div>
);

export const FadeUp = ({ children, delay = 0, distance = 16, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, y: distance }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ ...transitionDefaults, delay }}
    className={className}
  >
    {children}
  </motion.div>
);

export const ScaleIn = ({ children, delay = 0, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.96 }}
    animate={{ opacity: 1, scale: 1 }}
    transition={{ ...transitionDefaults, delay }}
    className={className}
  >
    {children}
  </motion.div>
);

export const StaggerContainer = ({ children, staggerDelay = 0.08, className = '' }) => (
  <motion.div
    initial="hidden"
    animate="show"
    variants={{
      hidden: { opacity: 0 },
      show: {
        opacity: 1,
        transition: {
          staggerChildren: staggerDelay,
        },
      },
    }}
    className={className}
  >
    {children}
  </motion.div>
);

export const StaggerItem = ({ children, className = '' }) => (
  <motion.div
    variants={{
      hidden: { opacity: 0, y: 12 },
      show: { opacity: 1, y: 0, transition: transitionDefaults },
    }}
    className={className}
  >
    {children}
  </motion.div>
);

export const HoverLift = ({ children, className = '' }) => (
  <motion.div
    whileHover={{ y: -3, transition: { duration: 0.2, ease: 'easeOut' } }}
    whileTap={{ scale: 0.99 }}
    className={className}
  >
    {children}
  </motion.div>
);

// Scroll-triggered Viewport Motion Components (Blur -> Focus, Directional Slides)
const scrollEase = [0.16, 1, 0.3, 1];
const viewportConfig = { once: false, amount: 0.25, margin: '-40px' };

export const ScrollBlurFocus = ({ children, delay = 0, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, filter: 'blur(8px)', scale: 0.98, y: 16 }}
    whileInView={{ opacity: 1, filter: 'blur(0px)', scale: 1, y: 0 }}
    viewport={viewportConfig}
    transition={{ duration: 0.7, ease: scrollEase, delay }}
    className={className}
  >
    {children}
  </motion.div>
);

export const ScrollSlideLeft = ({ children, delay = 0, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, x: -32, filter: 'blur(6px)' }}
    whileInView={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
    viewport={viewportConfig}
    transition={{ duration: 0.7, ease: scrollEase, delay }}
    className={className}
  >
    {children}
  </motion.div>
);

export const ScrollSlideRight = ({ children, delay = 0, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, x: 32, filter: 'blur(6px)' }}
    whileInView={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
    viewport={viewportConfig}
    transition={{ duration: 0.7, ease: scrollEase, delay }}
    className={className}
  >
    {children}
  </motion.div>
);

export const ScrollFadeUp = ({ children, delay = 0, distance = 24, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, y: distance, filter: 'blur(4px)' }}
    whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
    viewport={viewportConfig}
    transition={{ duration: 0.65, ease: scrollEase, delay }}
    className={className}
  >
    {children}
  </motion.div>
);

export const ScrollStaggerContainer = ({ children, staggerDelay = 0.1, className = '' }) => (
  <motion.div
    initial="hidden"
    whileInView="show"
    viewport={viewportConfig}
    variants={{
      hidden: { opacity: 0 },
      show: {
        opacity: 1,
        transition: {
          staggerChildren: staggerDelay,
        },
      },
    }}
    className={className}
  >
    {children}
  </motion.div>
);

export const ScrollStaggerItem = ({ children, className = '' }) => (
  <motion.div
    variants={{
      hidden: { opacity: 0, y: 20, filter: 'blur(6px)' },
      show: { opacity: 1, y: 0, filter: 'blur(0px)', transition: { duration: 0.6, ease: scrollEase } },
    }}
    className={className}
  >
    {children}
  </motion.div>
);
