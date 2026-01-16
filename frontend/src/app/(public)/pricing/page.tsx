'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Target, Check, ArrowLeft } from 'lucide-react';

export default function PricingPage() {
  const plans = [
    {
      name: 'Starter',
      price: 2,
      description: 'Perfect for getting started with goal setting',
      features: [
        'Unlimited active goals',
        'Advanced AI coaching',
        'Weekly check-ins',
        'Email reminders',
        'Goal templates',
      ],
      cta: 'Get Started',
      popular: true,
    },
    {
      name: 'Pro',
      price: 8,
      description: 'For serious achievers who want unlimited potential',
      features: [
        'Unlimited active goals',
        'Advanced AI coaching',
        'Daily check-ins',
        'Weekly check-ins',
        'Email reminders',
        'Goal templates',
        'Custom goal templates',
        'Progress analytics',
        'Calendar integration',
        'Export to PDF',
      ],
      cta: 'Go Pro',
      popular: false,
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Header */}
      <header className="container mx-auto px-4 py-6 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Target className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold">GoalGetter</span>
        </Link>
        <div className="flex items-center gap-4">
          <Link href="/login">
            <Button variant="ghost">Sign in</Button>
          </Link>
          <Link href="/signup">
            <Button>Get Started</Button>
          </Link>
        </div>
      </header>

      {/* Pricing Content */}
      <main className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <Link href="/" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6">
            <ArrowLeft className="h-4 w-4" />
            Back to home
          </Link>
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            Simple, Transparent Pricing
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Choose the plan that fits your ambition. Start achieving your goals today.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {plans.map((plan) => (
            <Card
              key={plan.name}
              className={`relative ${plan.popular ? 'border-primary shadow-lg' : ''}`}
            >
              {plan.popular && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2">
                  Most Popular
                </Badge>
              )}
              <CardHeader className="text-center pb-2">
                <CardTitle className="text-2xl">{plan.name}</CardTitle>
                <CardDescription>{plan.description}</CardDescription>
              </CardHeader>
              <CardContent className="text-center">
                <div className="mb-6">
                  <span className="text-5xl font-bold">${plan.price}</span>
                  <span className="text-muted-foreground">/month</span>
                </div>
                <ul className="space-y-3 text-left">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-3">
                      <Check className="h-5 w-5 text-primary flex-shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
              <CardFooter>
                <Link href="/signup" className="w-full">
                  <Button
                    className="w-full"
                    variant={plan.popular ? 'default' : 'outline'}
                    size="lg"
                  >
                    {plan.cta}
                  </Button>
                </Link>
              </CardFooter>
            </Card>
          ))}
        </div>

        <div className="text-center mt-12 text-muted-foreground">
          <p>All plans include a 7-day free trial. No credit card required.</p>
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
