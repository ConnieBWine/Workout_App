import React from 'react';
import { AlertTriangle, CheckCircle, XCircle, Info, Zap } from 'lucide-react';

/**
 * Feedback list component for displaying historical exercise feedback
 * 
 * This component shows a list of feedback items with their frequency and severity,
 * often used in summary views or historical analysis of exercise performance.
 * 
 * @param {Object} props - Component props
 * @param {Array} props.feedbackItems - Array of feedback items with count and severity
 * @param {string} props.title - Optional title for the feedback list
 * @param {string} props.className - Additional CSS classes
 */
const FeedbackList = ({ feedbackItems = [], title = 'Feedback', className = '' }) => {
  /**
   * Get icon and styling based on feedback severity
   * 
   * @param {string} severity - Feedback severity (HIGH, MEDIUM, LOW)
   * @param {string} feedbackText - The feedback text for contextual analysis
   * @returns {Object} Icon and styling information
   */
  const getSeverityStyles = (severity, feedbackText) => {
    // Default to medium if not specified
    const severityLevel = severity || 'MEDIUM';
    
    // Check for positive feedback regardless of severity
    const isPositive = /good|excellent|great|correct form|keep it up/i.test(feedbackText);
    
    if (isPositive) {
      return {
        icon: CheckCircle,
        bgColor: 'bg-green-50',
        borderColor: 'border-green-100',
        textColor: 'text-green-800',
        iconColor: 'text-green-500'
      };
    }
    
    // Apply styles based on severity
    switch (severityLevel.toUpperCase()) {
      case 'HIGH':
        return {
          icon: XCircle,
          bgColor: 'bg-red-50',
          borderColor: 'border-red-100',
          textColor: 'text-red-800',
          iconColor: 'text-red-500'
        };
      case 'MEDIUM':
        return {
          icon: AlertTriangle,
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-100',
          textColor: 'text-yellow-800',
          iconColor: 'text-yellow-500'
        };
      case 'LOW':
        return {
          icon: Info,
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-100',
          textColor: 'text-blue-800',
          iconColor: 'text-blue-500'
        };
      default:
        return {
          icon: Info,
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-100',
          textColor: 'text-gray-800',
          iconColor: 'text-gray-500'
        };
    }
  };

  // If no feedback, show placeholder message
  if (!feedbackItems || feedbackItems.length === 0) {
    return (
      <div className={`border rounded-md p-6 text-center ${className}`}>
        <Zap className="mx-auto h-10 w-10 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">No feedback available</h3>
        <p className="mt-1 text-sm text-gray-500">
          Complete more exercises to receive form feedback.
        </p>
      </div>
    );
  }

  return (
    <div className={className}>
      {title && (
        <h3 className="text-lg font-medium text-gray-900 mb-3">{title}</h3>
      )}
      
      <ul className="space-y-2">
        {feedbackItems.map((item, index) => {
          const feedbackText = item.text || item.feedback;
          const count = item.count || 1;
          const styles = getSeverityStyles(item.severity, feedbackText);
          const Icon = styles.icon;
          
          return (
            <li 
              key={index}
              className={`flex items-center p-3 rounded-md border ${styles.bgColor} ${styles.borderColor}`}
            >
              <div className="flex-shrink-0">
                <Icon className={`h-5 w-5 ${styles.iconColor}`} />
              </div>
              
              <div className="ml-3 flex-1">
                <p className={`text-sm font-medium ${styles.textColor}`}>
                  {feedbackText}
                </p>
              </div>
              
              {/* Feedback frequency badge */}
              {count > 1 && (
                <div className="ml-2 flex-shrink-0">
                  <span className={`
                    inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
                    ${styles.textColor} bg-opacity-80
                  `}>
                    {count}×
                  </span>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default FeedbackList;