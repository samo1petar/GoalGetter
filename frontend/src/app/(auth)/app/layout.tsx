'use client';

import { useState } from 'react';
import { Header } from '@/components/layout/Header';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Target, FileText, Calendar, Settings } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();

  const navItems = [
    { href: '/app', icon: FileText, label: 'Workspace' },
    { href: '/app/goals', icon: Target, label: 'Goals' },
    { href: '/app/meetings', icon: Calendar, label: 'Meetings' },
    { href: '/app/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="h-screen flex flex-col">
      <Header onMenuClick={() => setSidebarOpen(true)} />

      {/* Mobile sidebar */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <div className="flex items-center gap-2 p-4 border-b">
            <Target className="h-6 w-6 text-primary" />
            <span className="font-semibold">GoalGetter</span>
          </div>
          <nav className="p-2">
            {navItems.map((item) => (
              <Link key={item.href} href={item.href} onClick={() => setSidebarOpen(false)}>
                <Button
                  variant="ghost"
                  className={cn(
                    'w-full justify-start gap-2 mb-1',
                    pathname === item.href && 'bg-muted'
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Button>
              </Link>
            ))}
          </nav>
        </SheetContent>
      </Sheet>

      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
