import React from 'react';
import { Link } from 'react-router-dom';
import { Menu, Bell, User } from 'lucide-react';

/**
 * Application header component with navigation controls
 * 
 * This component displays the top navigation bar with the application title,
 * menu toggle for the sidebar, and user-related actions.
 * 
 * @param {Object} props - Component props
 * @param {Function} props.toggleSidebar - Function to toggle sidebar visibility
 */
const Header = ({ toggleSidebar }) => {
  return (
    <header className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left section: Logo and mobile menu button */}
          <div className="flex items-center">
            {/* Mobile menu button */}
            <button
              type="button"
              className="p-2 text-gray-600 rounded-md lg:hidden hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
              onClick={toggleSidebar}
              aria-label="Open sidebar"
            >
              <Menu className="w-6 h-6" />
            </button>
            
            {/* App logo/title */}
            <Link to="/" className="flex items-center ml-2 lg:ml-0">
              <svg 
                viewBox="0 0 24 24" 
                className="w-8 h-8 text-blue-600"
                fill="currentColor"
              >
                <path d="M13.5,3.5c0,0.83,0.67,1.5,1.5,1.5c0.83,0,1.5-0.67,1.5-1.5S15.83,2,15,2C14.17,2,13.5,2.67,13.5,3.5z M13.5,11.5c0,0.83,0.67,1.5,1.5,1.5c0.83,0,1.5-0.67,1.5-1.5S15.83,10,15,10C14.17,10,13.5,10.67,13.5,11.5z M13.5,19.5c0,0.83,0.67,1.5,1.5,1.5c0.83,0,1.5-0.67,1.5-1.5S15.83,18,15,18C14.17,18,13.5,18.67,13.5,19.5z M8.5,19.5c0,0.83,0.67,1.5,1.5,1.5c0.83,0,1.5-0.67,1.5-1.5S10.83,18,10,18C9.17,18,8.5,18.67,8.5,19.5z M8.5,11.5c0,0.83,0.67,1.5,1.5,1.5c0.83,0,1.5-0.67,1.5-1.5S10.83,10,10,10C9.17,10,8.5,10.67,8.5,11.5z M8.5,3.5c0,0.83,0.67,1.5,1.5,1.5c0.83,0,1.5-0.67,1.5-1.5S10.83,2,10,2C9.17,2,8.5,2.67,8.5,3.5z M4.5,3.5c0,0.83,0.67,1.5,1.5,1.5C6.83,5,7.5,4.33,7.5,3.5S6.83,2,6,2C5.17,2,4.5,2.67,4.5,3.5z M4.5,11.5c0,0.83,0.67,1.5,1.5,1.5c0.83,0,1.5-0.67,1.5-1.5S6.83,10,6,10C5.17,10,4.5,10.67,4.5,11.5z M4.5,19.5c0,0.83,0.67,1.5,1.5,1.5c0.83,0,1.5-0.67,1.5-1.5S6.83,18,6,18C5.17,18,4.5,18.67,4.5,19.5z" />
              </svg>
              <span className="ml-2 text-xl font-bold text-gray-900">FitTrack Pro</span>
            </Link>
          </div>
          
          {/* Right section: User actions */}
          <div className="flex items-center space-x-4">
            {/* Notifications button */}
            <button
              type="button"
              className="p-2 text-gray-500 rounded-full hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="View notifications"
            >
              <Bell className="w-6 h-6" />
            </button>
            
            {/* Profile dropdown */}
            <div className="relative">
              <Link
                to="/profile"
                className="flex items-center p-1 text-gray-500 rounded-full hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <span className="sr-only">Open user menu</span>
                <User className="w-6 h-6" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;