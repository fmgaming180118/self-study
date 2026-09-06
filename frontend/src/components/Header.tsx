'use client';

import Link from 'next/link';
import { 
  Menu, 
  Search, 
  User, 
  Bell, 
  GitBranch, 
  Code, 
  Zap, 
  Brain, 
  Cpu, 
  Settings,
  LogOut,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import type { User as AppUser } from '@/types';

type AppView = 'map' | 'tutor' | 'progress';

export const Header = ({ 
  user, 
  onViewChange, 
  currentView 
}: { 
  user: AppUser | null;
  onViewChange: (view: AppView) => void;
  currentView: AppView;
}) => {
  const router = useRouter();

  const handleLogout = () => {
    // In a real app, this would call an auth endpoint
    alert('Logging out...');
    router.push('/');
  };

  return (
    <header className="border-b border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-900">
      <div className="flex items-center justify-between px-4 py-3">
        {/* Left Side - Brand & Navigation */}
        <div className="flex items-center space-x-4">
          <Link href="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-xl text-dark-900 dark:text-dark-100">
              Self Study OS
            </span>
          </Link>
          
          <nav className="hidden md:flex items-center space-x-6 text-sm font-medium">
            <Link
              href="/"
              className={cn(
                'px-2 py-1 rounded transition-colors duration-200',
                currentView === 'map' ? 'text-primary-600 border-b-2 border-primary-500' : 'text-dark-500 dark:text-dark-400 hover:text-dark-600 dark:hover:text-dark-300'
              )}
              onClick={() => onViewChange('map')}
            >
              Skill Map
            </Link>
            <Link
              href="/"
              className={cn(
                'px-2 py-1 rounded transition-colors duration-200',
                currentView === 'progress' ? 'text-primary-600 border-b-2 border-primary-500' : 'text-dark-500 dark:text-dark-400 hover:text-dark-600 dark:hover:text-dark-300'
              )}
              onClick={() => onViewChange('progress')}
            >
              Progress
            </Link>
          </nav>
        </div>

        {/* Right Side - User & Controls */}
        <div className="flex items-center space-x-3">
          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 text-dark-500 dark:text-dark-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search skills, resources..."
              className="pl-10 pr-4 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-dark-50 dark:bg-dark-800 text-dark-900 dark:text-dark-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent w-32 md:w-48"
            />
          </div>

          {/* Notifications */}
          <div className="relative">
            <Bell className="w-5 h-5 text-dark-600 dark:text-dark-400 hover:text-dark-900 dark:hover:text-dark-100" />
            <div className="w-2 h-2 bg-primary-500 rounded-full absolute -top-1 -right-1" />
          </div>

          {/* User Menu */}
          <div className="relative">
            <button
              className="flex items-center space-x-2 p-2 rounded hover:bg-dark-100 dark:hover:bg-dark-800"
              onClick={(e) => {
                e.stopPropagation();
                // Toggle user menu (would use a dropdown in real implementation)
              }}
            >
              {user ? (
                <>
                  <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  <span className="hidden md:inline">{user.full_name?.split(' ')[0] || 'User'}</span>
                </>
              ) : (
                <User className="w-4 h-4 text-dark-600 dark:text-dark-400" />
              )}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
