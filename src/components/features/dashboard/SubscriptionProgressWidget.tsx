import React from 'react';

const SubscriptionProgressWidget = () => {
  return (
    <div className="p-4 rounded-lg bg-mint-dark/50">
      <h4 className="font-bold text-lg text-mint-accent mb-4">Your Crate</h4>
      <div>
        <div className="mb-2">
          <p className="text-sm text-mint-studio">Tracks Used</p>
          <div className="relative w-full h-4 bg-mint-secondary rounded-full overflow-hidden">
            <div className="absolute top-0 left-0 h-full w-1/4 bg-mint-gradient rounded-full"></div>
          </div>
          <p className="text-xs text-mint-accent text-right mt-1">5/20</p>
        </div>
        <div className="text-xs text-mint-accent">
          Crate refills in 12 days.
        </div>
      </div>
    </div>
  );
};

export default SubscriptionProgressWidget;
