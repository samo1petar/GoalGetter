'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { meetingsApi } from '@/lib/api/meetings';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Calendar,
  Clock,
  CheckCircle,
  XCircle,
  Video,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';

export default function MeetingsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const { data: meetingsData, isLoading } = useQuery({
    queryKey: ['meetings'],
    queryFn: () => meetingsApi.list({ page_size: 20 }),
  });

  const { data: nextMeeting } = useQuery({
    queryKey: ['meetings', 'next'],
    queryFn: meetingsApi.getNext,
    refetchInterval: 60000, // Refresh every minute
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
    scheduled: 'bg-blue-100 text-blue-800',
    active: 'bg-green-100 text-green-800',
    completed: 'bg-gray-100 text-gray-800',
    cancelled: 'bg-red-100 text-red-800',
  };

  const formatCountdown = (seconds: number) => {
    if (seconds <= 0) return 'Starting now!';

    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Meetings</h1>
          <p className="text-muted-foreground">
            {user?.phase === 'goal_setting'
              ? 'Set up recurring meetings to transition to tracking phase'
              : 'Your scheduled coaching sessions'}
          </p>
        </div>
      </div>

      {/* Next Meeting Card */}
      {nextMeeting?.meeting && (
        <Card className="mb-6 border-primary/50 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Video className="h-5 w-5" />
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

      {/* Current Phase Info */}
      {user?.phase === 'goal_setting' && (
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-full bg-yellow-100">
                <Clock className="h-6 w-6 text-yellow-700" />
              </div>
              <div className="flex-1">
                <h3 className="font-medium mb-1">You&apos;re in Goal Setting Phase</h3>
                <p className="text-sm text-muted-foreground mb-3">
                  You have unlimited access to your AI coach. When you&apos;re ready, set up
                  recurring meetings to transition to the tracking phase.
                </p>
                <Button size="sm">
                  <Calendar className="h-4 w-4 mr-2" />
                  Set Up Meetings
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
              <p className="text-muted-foreground">
                Set up recurring meetings to track your progress
              </p>
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
    </div>
  );
}
