import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle, CheckCircle, XCircle, Info } from 'lucide-react';

/**
 * Exercise feedback display component
 * 
 * This component renders real-time feedback about exercise form,
 * with appropriate visual indicators for different types of feedback.
 * It animates new feedback items for better visibility and supports
 * auto-dismissal of older feedback items.
 * 
 * @param {Object} props - Component props
 * @param {Array} props.feedback - Array of feedback strings
 * @param {string} props.className - Additional CSS classes
 * @param {number} props.dismissAfter - Time in ms after which feedback is dismissed (0 = never)
 */
const FeedbackDisplay = ({ feedback = [], className = '', dismissAfter = 8000 }) => {
  // State to track displayed feedback items with animations
  const [displayedFeedback, setDisplayedFeedback] = useState([]);
  
  // Reference to last feedback to detect changes
  const lastFeedbackRef = useRef([]);
  
  /**
   * Determine feedback type based on content
   * 
   * @param {string} feedbackText - The feedback text to analyze
   * @returns {Object} An object with type and icon information
   */
  const getFeedbackType = (feedbackText) => {
    const lowercaseFeedback = feedbackText.toLowerCase();
    
    // Positive feedback indicators
    if (
      lowercaseFeedback.includes('good') ||
      lowercaseFeedback.includes('great') ||
      lowercaseFeedback.includes('excellent') ||
      lowercaseFeedback.includes('correct form') ||
      lowercaseFeedback.includes('keep it up')
    ) {
      return { 
        type: 'success',
        icon: CheckCircle,
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        textColor: 'text-green-800',
        iconColor: 'text-green-500'
      };
    }
    
    // Warning feedback indicators
    if (
      lowercaseFeedback.includes('try to') ||
      lowercaseFeedback.includes('slightly') ||
      lowercaseFeedback.includes('consider')
    ) {
      return { 
        type: 'warning',
        icon: AlertTriangle,
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
        textColor: 'text-yellow-800',
        iconColor: 'text-yellow-400'
      };
    }
    
    // Error feedback indicators
    if (
      lowercaseFeedback.includes('don\'t') ||
      lowercaseFeedback.includes('keep your') ||
      lowercaseFeedback.includes('maintain') ||
      lowercaseFeedback.includes('lower') ||
      lowercaseFeedback.includes('raise')
    ) {
      return { 
        type: 'error',
        icon: XCircle,
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        textColor: 'text-red-800',
        iconColor: 'text-red-500'
      };
    }
    
    // Default feedback type
    return { 
      type: 'info',
      icon: Info,
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      textColor: 'text-blue-800',
      iconColor: 'text-blue-500'
    };
  };

  // Update displayed feedback when feedback prop changes
  useEffect(() => {
    // If feedback array has changed
    if (JSON.stringify(feedback) !== JSON.stringify(lastFeedbackRef.current)) {
      // Process new feedback items
      const newFeedback = feedback
        .filter(item => !lastFeedbackRef.current.includes(item))
        .map(item => ({
          id: `feedback-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
          text: item,
          timestamp: Date.now(),
          ...getFeedbackType(item),
          isNew: true
        }));
      
      // Add new feedback items to the displayed list
      if (newFeedback.length > 0) {
        setDisplayedFeedback(prev => [...newFeedback, ...prev].slice(0, 3));
        
        // Remove "new" flag after animation completes
        setTimeout(() => {
          setDisplayedFeedback(prev => 
            prev.map(item => ({
              ...item,
              isNew: false
            }))
          );
        }, 300);
      }
      
      // Update last feedback reference
      lastFeedbackRef.current = [...feedback];
    }
  }, [feedback]);

  // Set up auto-dismissal of feedback items
  useEffect(() => {
    if (dismissAfter > 0) {
      const now = Date.now();
      const timer = setTimeout(() => {
        setDisplayedFeedback(prev => 
          prev.filter(item => now - item.timestamp < dismissAfter)
        );
      }, dismissAfter);
      
      return () => clearTimeout(timer);
    }
  }, [displayedFeedback, dismissAfter]);

  // If no feedback to display, return empty container to maintain layout
  if (displayedFeedback.length === 0) {
    return <div className={`${className} h-16 flex items-center justify-center`} />;
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {displayedFeedback.map((item) => {
        const Icon = item.icon;
        
        return (
          <div 
            key={item.id}
            className={`
              flex items-center p-3 rounded-md border
              ${item.bgColor} ${item.borderColor}
              ${item.isNew ? 'animate-slide-in-right' : ''}
              transition-all duration-300
            `}
          >
            <Icon className={`h-5 w-5 ${item.iconColor} mr-2 flex-shrink-0`} />
            <span className={`text-sm font-medium ${item.textColor}`}>
              {item.text}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export default FeedbackDisplay;