"""
Feedback management system for exercise form analysis.

This module handles collecting, prioritizing, and delivering feedback to users
about their exercise form and technique.
"""
from enum import Enum
from collections import deque
import heapq
from typing import List, Tuple, Dict, Any


class FeedbackPriority(Enum):
    """Enum for feedback priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class FeedbackManager:
    """
    Manages exercise feedback collection, prioritization, and delivery.
    
    This class maintains a sliding window of recent feedback and uses a priority
    queue to determine the most important feedback to show to the user.
    """
    
    def __init__(self, window_size=5):
        """
        Initialize the feedback manager.
        
        Args:
            window_size (int): Size of the sliding window for feedback aggregation.
        """
        # Sliding window of recent feedback
        self.feedback_window = deque(maxlen=window_size)
        
        # Current aggregated feedback
        self.current_feedback = []
        
        # Priority queue for urgent feedback
        self.priority_queue = []
        
        # Track persistent issues that need addressing
        self.persistent_issues = {}
        
        # Cache of feedback already given to avoid repetition
        self.feedback_cache = set()
        
        # Counter for how many frames since last feedback was given
        self.frames_since_feedback = 0

    def add_feedback(self, feedback: str, priority: FeedbackPriority):
        """
        Add a new feedback item.
        
        Args:
            feedback (str): The feedback message.
            priority (FeedbackPriority): Priority level of the feedback.
        """
        # Add to priority queue with negative priority for max-heap behavior
        heapq.heappush(self.priority_queue, (-priority.value, feedback))
        
        # Add to sliding window
        self.feedback_window.append((feedback, priority))
        
        # Track persistent issues
        if feedback in self.persistent_issues:
            self.persistent_issues[feedback] += 1
        else:
            self.persistent_issues[feedback] = 1
        
        # Process the updated feedback
        self._process_feedback()
        
        # Reset frames counter
        self.frames_since_feedback = 0

    def _process_feedback(self):
        """
        Process the feedback window to determine current feedback to show.
        
        This method aggregates feedback in the sliding window and identifies
        the most frequent issues.
        """
        # Count occurrences of each feedback in the window
        feedback_count = {}
        for feedback, priority in self.feedback_window:
            if feedback in feedback_count:
                feedback_count[feedback] += 1
            else:
                feedback_count[feedback] = 1
        
        # Find feedback that occurs more than half the time in the window
        threshold = len(self.feedback_window) // 2
        self.current_feedback = [
            fb for fb, count in feedback_count.items() 
            if count > threshold
        ]

    def update_frame_counter(self):
        """Update the counter for frames since last feedback."""
        self.frames_since_feedback += 1

    def get_feedback(self, max_items=1, min_frames=15):
        """
        Get the most important feedback to show to the user.
        
        Args:
            max_items (int): Maximum number of feedback items to return.
            min_frames (int): Minimum frames between feedback to avoid overwhelming the user.
            
        Returns:
            list: List of feedback strings ordered by priority.
        """
        # Don't give feedback too frequently
        if self.frames_since_feedback < min_frames:
            return []
        
        # Reset frame counter if providing feedback
        self.frames_since_feedback = 0
        
        if not self.priority_queue:
            return []
        
        # Get the highest priority feedback items
        result = []
        temp_queue = []
        
        while self.priority_queue and len(result) < max_items:
            priority, feedback = heapq.heappop(self.priority_queue)
            
            # Only add if not recently given to avoid repetition
            if feedback not in self.feedback_cache:
                result.append(feedback)
                self.feedback_cache.add(feedback)
                
            # Keep the item in the queue for future consideration
            temp_queue.append((priority, feedback))
        
        # Restore the priority queue
        for item in temp_queue:
            heapq.heappush(self.priority_queue, item)
        
        # Limit the feedback cache size
        if len(self.feedback_cache) > 10:
            self.feedback_cache = set(list(self.feedback_cache)[-10:])
        
        return result

    def get_persistent_issues(self, min_occurrences=3):
        """
        Get issues that persistently occur.
        
        Args:
            min_occurrences (int): Minimum number of occurrences to consider an issue persistent.
            
        Returns:
            list: List of persistent feedback issues.
        """
        return [
            feedback for feedback, count in self.persistent_issues.items()
            if count >= min_occurrences
        ]

    def clear_feedback(self):
        """
        Clear all feedback data.
        
        This is typically called when switching exercises or restarting.
        """
        self.feedback_window.clear()
        self.current_feedback = []
        self.priority_queue = []
        self.feedback_cache = set()
        self.frames_since_feedback = 0
        
        # We keep persistent_issues for tracking across exercises

    def get_session_summary(self):
        """
        Get a summary of feedback for the session.
        
        Returns:
            dict: Summary of feedback with counts and priorities.
        """
        summary = {}
        for feedback, count in self.persistent_issues.items():
            if count >= 2:  # Only include significant issues
                summary[feedback] = {
                    'count': count,
                    'priority': 'HIGH' if count > 5 else 'MEDIUM'
                }
        
        return summary