'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { meetingsApi } from '@/lib/api/meetings';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Calendar,
  CalendarCheck,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Plus,
} from 'lucide-react';
import { toast } from 'sonner';

export default function MeetingsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  // Dialog state
  const [isScheduleDialogOpen, setIsScheduleDialogOpen] = useState(false);
  const [scheduledDateTime, setScheduledDateTime] = useState('');
  const [duration, setDuration] = useState('30');

  const { data: meetingsData, isLoading } = useQuery({
    queryKey: ['meetings'],
    queryFn: () => meetingsApi.list({ page_size: 20 }),
  });

  const { data: nextMeeting } = useQuery({
    queryKey: ['meetings', 'next'],
    queryFn: meetingsApi.getNext,
    refetchInterval: 60000, // Refresh every minute
  });

  const createMutation = useMutation({
    mutationFn: meetingsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      toast.success('Meeting scheduled! Check your email for the calendar invite.');
      setIsScheduleDialogOpen(false);
      resetForm();
    },
    onError: () => {
      toast.error('Failed to schedule meeting');
    },
  });

  const completeMutation = useMutation({
    mutationFn: (meetingId: string) => meetingsApi.complete(meetingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      toast.success('Meeting marked as complete');
    },
    onError: () => {
      toast.error('Failed to complete meeting');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (meetingId: string) => meetingsApi.cancel(meetingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      toast.success('Meeting cancelled');
    },
    onError: () => {
      toast.error('Failed to cancel meeting');
    },
  });

  const meetings = meetingsData?.meetings || [];

  const statusColors: Record<string, string> = {
    scheduled: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    completed: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
    cancelled: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  };

  const formatCountdown = (seconds: number | null | undefined) => {
    if (seconds === null || seconds === undefined || seconds <= 0) return 'Starting now!';

    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const resetForm = () => {
    setScheduledDateTime('');
    setDuration('30');
  };

  const handleScheduleMeeting = () => {
    if (!scheduledDateTime) {
      toast.error('Please select a date and time');
      return;
    }

    // Convert local datetime to ISO string
    const scheduledAt = new Date(scheduledDateTime).toISOString();

    createMutation.mutate({
      scheduled_at: scheduledAt,
      duration_minutes: parseInt(duration, 10),
    });
  };

  // Get minimum datetime (now + 1 hour)
  const getMinDateTime = () => {
    const now = new Date();
    now.setHours(now.getHours() + 1);
    now.setMinutes(0);
    return now.toISOString().slice(0, 16);
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Meetings</h1>
          <p className="text-muted-foreground">
            {user?.phase === 'goal_setting'
              ? 'Schedule coaching sessions to stay accountable'
              : 'Your scheduled coaching sessions'}
          </p>
        </div>
        <Button onClick={() => setIsScheduleDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Schedule Meeting
        </Button>
      </div>

      {/* Meetings Explanation Card */}
      <Card className="mb-6 bg-muted/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-full bg-primary/10">
              <CalendarCheck className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium mb-2">What are Meetings?</h3>
              <p className="text-sm text-muted-foreground">
                Meetings are scheduled coaching sessions with Alfred, your AI Coach,
                right here on GoalGetter. They&apos;re not about limiting your access to
                the app - they&apos;re a powerful tool to keep you accountable and strengthen
                your commitment to achieving your goals. Regular check-ins help you
                stay focused and make consistent progress.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Next Meeting Card */}
      {nextMeeting?.meeting && (
        <Card className="mb-6 border-primary/50 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CalendarCheck className="h-5 w-5" />
              Next Meeting
            </CardTitle>
            <CardDescription>
              {new Date(nextMeeting.meeting.scheduled_at).toLocaleDateString(undefined, {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-3xl font-bold text-primary">
                  {new Date(nextMeeting.meeting.scheduled_at).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
                <div className="text-sm text-muted-foreground">
                  {nextMeeting.meeting.duration_minutes} minutes
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-muted-foreground">Starts in</div>
                <div className="text-xl font-semibold">
                  {formatCountdown(nextMeeting.countdown_seconds)}
                </div>
                {nextMeeting.can_access_now && (
                  <Badge className="mt-1 bg-green-500">Chat Available</Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Current Phase Info - shown when no meetings */}
      {user?.phase === 'goal_setting' && meetings.length === 0 && (
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-full bg-yellow-100 dark:bg-yellow-900">
                <Clock className="h-6 w-6 text-yellow-700 dark:text-yellow-300" />
              </div>
              <div className="flex-1">
                <h3 className="font-medium mb-1">You&apos;re in Goal Setting Phase</h3>
                <p className="text-sm text-muted-foreground mb-3">
                  You have unlimited access to your AI coach. Schedule a meeting to stay
                  accountable and get a calendar reminder.
                </p>
                <Button size="sm" onClick={() => setIsScheduleDialogOpen(true)}>
                  <Calendar className="h-4 w-4 mr-2" />
                  Schedule Your First Meeting
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Meetings List */}
      <div className="space-y-3">
        <h2 className="font-semibold text-lg">All Meetings</h2>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : meetings.length === 0 ? (
          <Card className="text-center py-12">
            <CardContent>
              <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No meetings scheduled</h3>
              <p className="text-muted-foreground mb-4">
                Schedule a meeting to stay accountable and receive calendar reminders
              </p>
              <Button onClick={() => setIsScheduleDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Schedule Meeting
              </Button>
            </CardContent>
          </Card>
        ) : (
          meetings.map((meeting) => (
            <Card key={meeting.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      {new Date(meeting.scheduled_at).toLocaleDateString(undefined, {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric',
                      })}
                      <Badge className={statusColors[meeting.status]} variant="secondary">
                        {meeting.status}
                      </Badge>
                    </CardTitle>
                    <CardDescription className="flex items-center gap-2 mt-1">
                      <Clock className="h-3 w-3" />
                      {new Date(meeting.scheduled_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                      <span>&middot;</span>
                      {meeting.duration_minutes} min
                    </CardDescription>
                  </div>
                  {meeting.status === 'scheduled' && (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => completeMutation.mutate(meeting.id)}
                        disabled={completeMutation.isPending}
                      >
                        <CheckCircle className="h-4 w-4 mr-1" />
                        Complete
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => cancelMutation.mutate(meeting.id)}
                        disabled={cancelMutation.isPending}
                      >
                        <XCircle className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              {meeting.notes && (
                <CardContent className="pt-0">
                  <p className="text-sm text-muted-foreground">{meeting.notes}</p>
                </CardContent>
              )}
            </Card>
          ))
        )}
      </div>

      {/* Schedule Meeting Dialog */}
      <Dialog open={isScheduleDialogOpen} onOpenChange={setIsScheduleDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Schedule a Meeting</DialogTitle>
            <DialogDescription>
              Schedule a coaching session with Alfred. You&apos;ll receive a calendar invitation via email.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="datetime">Date and Time</Label>
              <Input
                id="datetime"
                type="datetime-local"
                value={scheduledDateTime}
                onChange={(e) => setScheduledDateTime(e.target.value)}
                min={getMinDateTime()}
                className="w-full"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="duration">Duration</Label>
              <Select value={duration} onValueChange={setDuration}>
                <SelectTrigger>
                  <SelectValue placeholder="Select duration" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="15">15 minutes</SelectItem>
                  <SelectItem value="30">30 minutes</SelectItem>
                  <SelectItem value="45">45 minutes</SelectItem>
                  <SelectItem value="60">1 hour</SelectItem>
                  <SelectItem value="90">1.5 hours</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsScheduleDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleScheduleMeeting} disabled={createMutation.isPending}>
              {createMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Scheduling...
                </>
              ) : (
                <>
                  <Calendar className="h-4 w-4 mr-2" />
                  Schedule Meeting
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
