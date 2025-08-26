// frontend/src/components/ui/GroupCard/hooks/useGroupCardState.ts

import { useState } from 'react';

export const useGroupCardState = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState<string | null>(null);

  return {
    isExpanded,
    setIsExpanded,
    operationInProgress,
    setOperationInProgress
  };
};