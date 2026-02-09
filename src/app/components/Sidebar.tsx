import React from 'react';
import SubscriptionProgressWidget from './SubscriptionProgressWidget';

const Sidebar = () => {
  return (
    <aside className="w-64 p-4 space-y-8">
      <SubscriptionProgressWidget />
    </aside>
  );
};

export default Sidebar;
