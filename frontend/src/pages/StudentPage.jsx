import React from 'react';
import { ChatInterface } from '../components/ChatInterface';

export const StudentPage = () => {
  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-64px)] min-h-0 overflow-hidden bg-raxel-soft-white w-full">
      <ChatInterface />
    </div>
  );
};

export default StudentPage;
