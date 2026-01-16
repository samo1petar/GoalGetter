'use client';

import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import {
  Target,
  Settings,
  LogOut,
  Calendar,
  FileText,
  Menu,
} from 'lucide-react';
import { ThemeToggle } from '@/components/common/ThemeToggle';

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { logout } = useAuth();
  const { user } = useAuthStore();

  const initials = user?.name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase() || 'U';

  return (
    <header className="h-14 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-full items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={onMenuClick}
          >
            <Menu className="h-5 w-5" />
          </Button>

          <Link href="/app" className="flex items-center gap-2">
            <Target className="h-6 w-6 text-primary" />
            <span className="font-semibold hidden sm:inline">GoalGetter</span>
          </Link>

          <nav className="hidden lg:flex items-center gap-1 ml-4">
            <Link href="/app">
              <Button variant="ghost" size="sm">
                <FileText className="h-4 w-4 mr-2" />
                Workspace
              </Button>
            </Link>
            <Link href="/app/goals">
              <Button variant="ghost" size="sm">
                <Target className="h-4 w-4 mr-2" />
                Goals
              </Button>
            </Link>
            <Link href="/app/meetings">
              <Button variant="ghost" size="sm">
                <Calendar className="h-4 w-4 mr-2" />
                Meetings
              </Button>
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {user?.phase && (
            <Badge variant={user.phase === 'goal_setting' ? 'default' : 'secondary'}>
              {user.phase === 'goal_setting' ? 'Goal Setting' : 'Tracking'}
            </Badge>
          )}

          <ThemeToggle />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={user?.profile_image || undefined} alt={user?.name} />
                  <AvatarFallback>{initials}</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user?.name}</p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {user?.email}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <Link href="/app/settings">
                <DropdownMenuItem className="cursor-pointer">
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </DropdownMenuItem>
              </Link>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="cursor-pointer text-destructive">
                <LogOut className="mr-2 h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
