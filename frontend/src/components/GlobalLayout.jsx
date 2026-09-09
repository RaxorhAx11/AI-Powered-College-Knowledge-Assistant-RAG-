import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Footer } from './Footer';
import { ContactSalesModal } from './ContactSalesModal';
import { TopProgressBar } from './motion/TopProgressBar';

export const GlobalLayout = ({ children }) => {
  const [salesModalOpen, setSalesModalOpen] = useState(false);
  const location = useLocation();

  // Chat route (/student) handles scroll inside the chat panel (exact match)
  const isChatRoute = location.pathname === '/student';
  const isAuthRoute = location.pathname === '/login' || location.pathname === '/signup';

  return (
    <div className="flex flex-col min-h-screen w-full bg-raxel-soft-white text-raxel-ink antialiased relative">
      <TopProgressBar />
      {/* Shared Navbar across all routes */}
      <Navbar onOpenContactSales={() => setSalesModalOpen(true)} />

      {/* Main Content Area */}
      <main className={`flex-1 w-full flex flex-col bg-raxel-soft-white ${isChatRoute ? 'h-[calc(100vh-64px)] overflow-hidden' : 'min-h-0'}`}>
        {children}
      </main>

      {/* Shared Footer (hidden on chat and auth routes) */}
      {!isChatRoute && !isAuthRoute && (
        <Footer onOpenContactSales={() => setSalesModalOpen(true)} />
      )}

      {/* Shared Contact Sales Modal */}
      <ContactSalesModal
        isOpen={salesModalOpen}
        onClose={() => setSalesModalOpen(false)}
      />
    </div>
  );
};

export default GlobalLayout;
