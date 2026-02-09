'use client';

import React from 'react';
import { useUser, UserStatus } from '@/app/context/UserContext';

const Username = () => {
  const { userStatus, setUserStatus } = useUser();

  const isSuper = userStatus === 'SuperFan';
  const superStyles = isSuper ? 'bg-super-gradient bg-clip-text text-transparent' : '';

  const toggleUserStatus = () => {
    setUserStatus(userStatus === 'RegularUser' ? 'SuperFan' : 'RegularUser');
  };

  return (
    <div className="flex items-center space-x-2">
      <span className={`font-bold ${superStyles}`}>
        {userStatus === 'SuperFan' ? 'SuperFan' : 'RegularUser'}
      </span>
      <button
        onClick={toggleUserStatus}
        className="text-xs bg-mint-secondary text-white px-2 py-1 rounded-full"
      >
        Toggle
      </button>
    </div>
  );
};

export default Username;
