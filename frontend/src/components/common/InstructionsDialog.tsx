'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { HelpCircle, Target, MessageSquare, Calendar, FileText, Sparkles } from 'lucide-react';

export function InstructionsDialog() {
  const steps = [
    {
      icon: Target,
      title: 'Set Your Goals',
      description: 'Start by creating your goals in the Goals section. Use our templates (SMART, OKR) or create custom goals tailored to your needs.',
    },
    {
      icon: MessageSquare,
      title: 'Chat with AI Coach',
      description: 'Use the Workspace to chat with your AI coach. Get personalized guidance, break through barriers, and refine your goals.',
    },
    {
      icon: FileText,
      title: 'Track Progress',
      description: 'Update your goals as you make progress. Add milestones, set deadlines, and mark achievements along the way.',
    },
    {
      icon: Calendar,
      title: 'Schedule Check-ins',
      description: 'Set up regular meetings with your AI coach to stay accountable. Get reminders and keep your momentum going.',
    },
    {
      icon: Sparkles,
      title: 'Achieve & Celebrate',
      description: 'Complete your goals and celebrate your achievements. Review your progress and set new ambitious goals.',
    },
  ];

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <HelpCircle className="h-4 w-4 mr-2" />
          Instructions
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            How to Use GoalGetter
          </DialogTitle>
          <DialogDescription>
            Follow these steps to get the most out of your goal-setting journey.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          {steps.map((step, index) => (
            <div key={step.title} className="flex gap-4">
              <div className="flex-shrink-0">
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <step.icon className="h-5 w-5 text-primary" />
                </div>
              </div>
              <div>
                <h3 className="font-semibold flex items-center gap-2">
                  <span className="text-xs bg-muted px-2 py-0.5 rounded-full">
                    Step {index + 1}
                  </span>
                  {step.title}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-6 p-4 bg-muted rounded-lg">
          <p className="text-sm text-muted-foreground">
            <strong>Tip:</strong> Start with one goal and focus on making progress before adding more. Quality over quantity leads to better results.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
