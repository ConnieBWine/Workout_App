import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  Home, 
  Dumbbell, 
  Calendar, 
  BarChart2, 
  MessageSquare, 
  User,
  X
} from 'lucide-react';

/**
 * Application sidebar navigation component
 * 
 * This component provides the main navigation menu with links to all major
 * sections of the application. It highlights the currently active route.
 * 
 * @param {Object} props - Component props
 * @param {boolean} props.isOpen - Whether sidebar is open (for mobile)
 * @param {Function} props.onClose - Function to close sidebar on mobile
 */
const Sidebar = ({ isOpen, onClose }) => {
  const location = useLocation();
  
  // Navigation items configuration
  const navItems = [
    { name: 'Dashboard', path: '/', icon: Home },
    { name: 'Exercise Tracker', path: '/exercise', icon: Dumbbell },
    { name: 'Workout Planner', path: '/workout', icon: Calendar },
    { name: 'Workout History', path: '/history', icon: BarChart2 },
    { name: 'AI Coach', path: '/ai-chat', icon: MessageSquare },
    { name: 'Profile', path: '/profile', icon: User },
  ];
  
  // Helper to determine if a nav item is active
  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === path;
    }
    return location.pathname.startsWith(path);
  };
  
  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:flex lg:flex-shrink-0">
        <div className="flex flex-col w-64">
          <div className="flex flex-col flex-1 min-h-0 bg-gray-800">
            <div className="flex items-center justify-center flex-shrink-0 h-16 px-4 bg-gray-900">
              <span className="text-xl font-bold text-white">FitTrack Pro</span>
            </div>
            <div className="flex flex-col flex-1 overflow-y-auto">
              <nav className="flex-1 px-2 py-4 space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.path);
                  
                  return (
                    <NavLink
                      key={item.name}
                      to={item.path}
                      className={`flex items-center px-2 py-2 text-sm font-medium rounded-md group ${
                        active
                          ? 'bg-gray-900 text-white'
                          : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                      }`}
                    >
                      <Icon className={`mr-3 flex-shrink-0 h-6 w-6 ${
                        active ? 'text-blue-400' : 'text-gray-400 group-hover:text-gray-300'
                      }`} />
                      {item.name}
                    </NavLink>
                  );
                })}
              </nav>
            </div>
          </div>
        </div>
      </div>
      
      {/* Mobile sidebar */}
      <div
        className={`fixed inset-0 z-40 flex lg:hidden transition-opacity duration-300 ease-linear ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
      >
        <div
          className={`relative flex flex-col flex-1 w-full max-w-xs pt-5 pb-4 bg-gray-800 transition-transform duration-300 ease-in-out ${
            isOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          {/* Close button */}
          <div className="absolute top-0 right-0 pt-2 pr-2">
            <button
              type="button"
              className="flex items-center justify-center w-10 h-10 ml-1 rounded-full"
              onClick={onClose}
            >
              <X className="w-6 h-6 text-white" />
              <span className="sr-only">Close sidebar</span>
            </button>
          </div>
          
          {/* Mobile sidebar header */}
          <div className="flex items-center flex-shrink-0 px-4">
            <span className="text-xl font-bold text-white">FitTrack Pro</span>
          </div>
          
          {/* Mobile navigation */}
          <div className="flex flex-col flex-1 h-0 mt-5 overflow-y-auto">
            <nav className="flex-1 px-2 space-y-1 bg-gray-800">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.path);
                
                return (
                  <NavLink
                    key={item.name}
                    to={item.path}
                    className={`flex items-center px-2 py-2 text-base font-medium rounded-md group ${
                      active
                        ? 'bg-gray-900 text-white'
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    }`}
                    onClick={onClose}
                  >
                    <Icon className={`mr-4 flex-shrink-0 h-6 w-6 ${
                      active ? 'text-blue-400' : 'text-gray-400 group-hover:text-gray-300'
                    }`} />
                    {item.name}
                  </NavLink>
                );
              })}
            </nav>
          </div>
        </div>
        
        {/* Empty div to capture clicks outside sidebar */}
        <div className="flex-shrink-0 w-14" aria-hidden="true" onClick={onClose} />
      </div>
    </>
  );
};

export default Sidebar;