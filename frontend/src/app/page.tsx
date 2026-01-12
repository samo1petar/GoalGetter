'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { Target, ArrowRight, Sparkles, Calendar, MessageSquare } from 'lucide-react';
import Link from 'next/link';

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/app');
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Header */}
      <header className="container mx-auto px-4 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold">GoalGetter</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login">
            <Button variant="ghost">Sign in</Button>
          </Link>
          <Link href="/signup">
            <Button>Get Started</Button>
          </Link>
        </div>
      </header>

      {/* Hero */}
      <main className="container mx-auto px-4 py-20">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-5xl font-bold tracking-tight mb-6">
            Transform Your Goals Into{' '}
            <span className="text-primary">Achievements</span>
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            Get personalized AI coaching inspired by Tony Robbins to help you set,
            track, and achieve your most ambitious goals.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/signup">
              <Button size="lg" className="gap-2">
                Start Free <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline">
                Sign In
              </Button>
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-20 max-w-5xl mx-auto">
          <div className="p-6 rounded-lg border bg-card">
            <div className="p-3 rounded-full bg-primary/10 w-fit mb-4">
              <Sparkles className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold mb-2">AI-Powered Coaching</h3>
            <p className="text-muted-foreground">
              Get real-time guidance from an AI coach that understands your goals
              and helps you break through barriers.
            </p>
          </div>

          <div className="p-6 rounded-lg border bg-card">
            <div className="p-3 rounded-full bg-primary/10 w-fit mb-4">
              <MessageSquare className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Smart Goal Editor</h3>
            <p className="text-muted-foreground">
              Use our intuitive split-screen editor to write and refine your goals
              while chatting with your AI coach.
            </p>
          </div>

          <div className="p-6 rounded-lg border bg-card">
            <div className="p-3 rounded-full bg-primary/10 w-fit mb-4">
              <Calendar className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Scheduled Check-ins</h3>
            <p className="text-muted-foreground">
              Transition to tracking mode with regular meeting reminders to keep
              you accountable and on track.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 border-t mt-20">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Target className="h-4 w-4" />
            <span>GoalGetter</span>
          </div>
          <p>AI-powered goal achievement platform</p>
        </div>
      </footer>
    </div>
  );
}
