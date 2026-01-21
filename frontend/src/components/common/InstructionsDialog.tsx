'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { HelpCircle, Target, MessageSquare, Calendar, FileText, Sparkles, ChevronRight, ArrowLeft } from 'lucide-react';

interface StepDetail {
  icon: React.ElementType;
  title: string;
  description: string;
  detailedInstructions: string[];
}

const steps: StepDetail[] = [
  {
    icon: Target,
    title: 'Set Your Goals',
    description: 'Start by creating your goals in the Goals section. Use our templates (SMART, OKR) or create custom goals tailored to your needs.',
    detailedInstructions: [
      'Step 1: Click on "Goals" in the top navigation bar. This will take you to the Goals page where you can see all your goals.',
      'Step 2: Look for the "New Goal" or "Create Goal" button. It\'s usually in the top right corner of the page. Click on it.',
      'Step 3: You\'ll see a form or editor appear. First, give your goal a clear title. For example, instead of "Get fit", write "Lose 10 pounds in 3 months" - be specific!',
      'Step 4: Choose a template if you want help structuring your goal. We offer SMART goals (Specific, Measurable, Achievable, Relevant, Time-bound) and OKR (Objectives and Key Results). If you\'re not sure, SMART is great for beginners.',
      'Step 5: Fill in the details of your goal. Write down WHY this goal matters to you. The more detail you add, the better your AI coach can help you.',
      'Step 6: Set a deadline for your goal. Having a target date creates urgency and helps you stay focused.',
      'Step 7: Click "Save" or "Create" to save your goal. Congratulations! You\'ve created your first goal!',
      'Pro Tip: Start with just ONE goal. It\'s tempting to add many goals at once, but focusing on one goal at a time dramatically increases your chances of success.',
    ],
  },
  {
    icon: MessageSquare,
    title: 'Chat with AI Coach',
    description: 'Use the Workspace to chat with your AI coach. Get personalized guidance, break through barriers, and refine your goals.',
    detailedInstructions: [
      'Step 1: Click on "Workspace" in the top navigation bar. This is your main area for interacting with your AI coach.',
      'Step 2: You\'ll see a chat interface on the screen. This is where you talk to Tony, your AI coach inspired by Tony Robbins\' coaching methodology.',
      'Step 3: Type your message in the text box at the bottom of the chat. You can ask anything about your goals, challenges, or need motivation.',
      'Step 4: Press Enter or click the Send button to send your message. Wait a moment while Tony processes your message and responds.',
      'Step 5: Read Tony\'s response carefully. He might ask you follow-up questions to better understand your situation. Answer honestly!',
      'Example messages you can try:\n- "I want to lose weight but I keep failing. Can you help me?"\n- "How do I break down my goal into smaller steps?"\n- "I\'m feeling unmotivated today. What should I do?"\n- "Can you help me make my goal more specific?"',
      'Step 6: The conversation is saved automatically. You can come back anytime and continue where you left off.',
      'Pro Tip: Be honest and specific with your coach. The more context you provide about your challenges, fears, and obstacles, the better advice you\'ll receive.',
      'Important: Your AI coach is here to guide you, challenge you, and keep you accountable. Don\'t just ask for advice - commit to taking action on the suggestions!',
    ],
  },
  {
    icon: FileText,
    title: 'Track Progress',
    description: 'Update your goals as you make progress. Add milestones, set deadlines, and mark achievements along the way.',
    detailedInstructions: [
      'Step 1: Go to the "Goals" section by clicking "Goals" in the navigation bar.',
      'Step 2: Find the goal you want to update and click on it to open it.',
      'Step 3: Look for an "Edit" button or simply click on the goal content to start editing.',
      'Step 4: Update your progress. You can:\n- Add notes about what you\'ve accomplished\n- Update the percentage complete\n- Add new milestones (smaller goals within your big goal)\n- Mark milestones as complete when you achieve them',
      'Step 5: Adding Milestones - Milestones are mini-goals that help you track progress. For example, if your goal is "Lose 10 pounds", your milestones might be:\n- Week 1: Start going to gym 3x per week\n- Week 2: Lose first 2 pounds\n- Week 4: Lose 5 pounds\n- Week 8: Lose 8 pounds',
      'Step 6: Setting Deadlines - Each milestone should have its own deadline. This creates a roadmap for your success.',
      'Step 7: Save your changes by clicking the "Save" button.',
      'Step 8: Celebrate your wins! Every time you complete a milestone, take a moment to acknowledge your progress. This builds momentum.',
      'Pro Tip: Update your goals at least once a week. Regular check-ins help you stay on track and catch problems early.',
      'Warning: If you\'re falling behind, don\'t give up! Talk to your AI coach about adjusting your plan. It\'s better to adjust than to quit.',
    ],
  },
  {
    icon: Calendar,
    title: 'Schedule Check-ins',
    description: 'Set up regular meetings with your AI coach to stay accountable. Get reminders and keep your momentum going.',
    detailedInstructions: [
      'Step 1: Click on "Meetings" in the top navigation bar.',
      'Step 2: You\'ll see your meeting schedule. If you haven\'t set up meetings yet, look for a "Set Up Meetings" or "Schedule" button.',
      'Step 3: Choose how often you want to meet with your AI coach. We recommend:\n- Weekly meetings for most goals\n- Every 3 days for urgent or challenging goals\n- Bi-weekly for long-term goals',
      'Step 4: Select your preferred meeting duration. A 30-minute check-in is usually enough to review progress and plan next steps.',
      'Step 5: Choose your preferred time and days. Pick a time when you\'re usually free and mentally fresh.',
      'Step 6: Enable email reminders so you don\'t forget your check-ins. Go to Settings to turn on notifications.',
      'Step 7: Save your meeting preferences.',
      'What happens during a check-in:\n- Your AI coach will ask about your progress\n- You\'ll discuss any obstacles you\'re facing\n- You\'ll set intentions for the next period\n- You\'ll get accountability and motivation',
      'Step 8: When it\'s time for your meeting, go to the Workspace. Your coach will know it\'s meeting time and will guide the conversation.',
      'Pro Tip: Treat these meetings like real appointments. Don\'t skip them! Consistency is the key to achieving your goals.',
      'If you miss a meeting: Don\'t worry! Just reschedule and get back on track. One missed meeting won\'t ruin your progress.',
    ],
  },
  {
    icon: Sparkles,
    title: 'Achieve & Celebrate',
    description: 'Complete your goals and celebrate your achievements. Review your progress and set new ambitious goals.',
    detailedInstructions: [
      'Step 1: When you\'ve completed all milestones and achieved your goal, go to the "Goals" section.',
      'Step 2: Open the goal you\'ve completed.',
      'Step 3: Mark the goal as "Completed". Look for a status dropdown or a "Mark Complete" button.',
      'Step 4: CELEBRATE! This is important. Take time to acknowledge what you\'ve accomplished:\n- Tell someone about your achievement\n- Treat yourself to something nice\n- Write down how it feels to succeed\n- Take a moment of gratitude',
      'Step 5: Reflect on your journey. Ask yourself:\n- What worked well?\n- What was challenging?\n- What would I do differently next time?\n- What did I learn about myself?',
      'Step 6: Share your success with your AI coach! Go to the Workspace and tell Tony about your achievement. He\'ll celebrate with you and help you reflect.',
      'Step 7: Review your completed goals. You can see all your past achievements in the Goals section by filtering for "Completed" goals.',
      'Step 8: Set a NEW goal! Success breeds success. Use the momentum from your achievement to tackle something new and even more ambitious.',
      'Pro Tip: Keep a success journal. Write down every goal you complete, no matter how small. On tough days, read through your wins to remind yourself what you\'re capable of.',
      'Remember: Every completed goal is proof that you CAN achieve what you set your mind to. You\'re building a track record of success!',
      'What\'s next? Don\'t rest too long! Within a day or two of completing a goal, set your next goal. Momentum is powerful - use it!',
    ],
  },
];

export function InstructionsDialog() {
  const [selectedStep, setSelectedStep] = useState<number | null>(null);

  const currentStep = selectedStep !== null ? steps[selectedStep] : null;
  const stepData = currentStep!; // Safe: only used when selectedStep !== null

  return (
    <Dialog onOpenChange={(open) => !open && setSelectedStep(null)}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <HelpCircle className="h-4 w-4 mr-2" />
          Instructions
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        {selectedStep === null ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Target className="h-5 w-5 text-primary" />
                How to Use GoalGetter
              </DialogTitle>
              <DialogDescription>
                Follow these steps to get the most out of your goal achievement journey. Click "Learn more" for detailed instructions.
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
                  <div className="flex-1">
                    <h3 className="font-semibold flex items-center gap-2">
                      <span className="text-xs bg-muted px-2 py-0.5 rounded-full">
                        Step {index + 1}
                      </span>
                      {step.title}
                    </h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      {step.description}
                    </p>
                    <button
                      onClick={() => setSelectedStep(index)}
                      className="text-primary hover:underline text-sm font-medium inline-flex items-center gap-1 mt-1"
                    >
                      Learn more <ChevronRight className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">
                <strong>Tip:</strong> Start with a small number of goals (3-5 max) and focus on making progress before adding more. Quality over quantity leads to better results.
              </p>
            </div>
          </>
        ) : (
          <>
            <DialogHeader>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedStep(null)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <ArrowLeft className="h-5 w-5" />
                </button>
                <DialogTitle className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <stepData.icon className="h-4 w-4 text-primary" />
                  </div>
                  Step {selectedStep + 1}: {stepData.title}
                </DialogTitle>
              </div>
              <DialogDescription>
                Detailed instructions to help you succeed
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              {stepData.detailedInstructions.map((instruction, i) => (
                <div key={i} className="text-sm">
                  {instruction.includes('\n') ? (
                    <div className="space-y-2">
                      {instruction.split('\n').map((line, j) => (
                        <p key={j} className={j === 0 ? 'font-medium' : 'text-muted-foreground pl-4'}>
                          {line}
                        </p>
                      ))}
                    </div>
                  ) : instruction.startsWith('Pro Tip:') || instruction.startsWith('Warning:') || instruction.startsWith('Important:') || instruction.startsWith('Remember:') ? (
                    <div className={`p-3 rounded-lg ${instruction.startsWith('Warning:') ? 'bg-destructive/10' : 'bg-primary/10'}`}>
                      <p className="font-medium">{instruction}</p>
                    </div>
                  ) : (
                    <p className="text-muted-foreground">{instruction}</p>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-6">
              <Button variant="outline" onClick={() => setSelectedStep(null)} className="w-full">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to all steps
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
