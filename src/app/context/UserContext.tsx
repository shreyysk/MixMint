'use client';

import React, { createContext, useState, useContext, ReactNode } from 'react';

export type UserStatus = 'RegularUser' | 'SuperFan';

interface UserContextType {
  userStatus: UserStatus;
  setUserStatus: (status: UserStatus) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};

export const UserProvider = ({ children }: { children: ReactNode }) => {
  const [userStatus, setUserStatus] = useState<UserStatus>('RegularUser');

  const value = {
    userStatus,
    setUserStatus,
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
};
