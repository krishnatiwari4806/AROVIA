import React from 'react';
import { InterviewRoom } from '../components/interview/InterviewRoom';

/**
 * InterviewSession Page Component Wrapper.
 * Forwards directly to the authoritative live InterviewRoom component.
 */
export function InterviewSession(props) {
  return <InterviewRoom {...props} />;
}

export default InterviewSession;
