'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { User, Bell, Trash2, Loader2, Save } from 'lucide-react';
import { toast } from 'sonner';
import type { User as UserType } from '@/types';
import { TwoFactorSetup } from '@/components/settings/TwoFactorSetup';

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore();
  const { logout } = useAuth();
  const queryClient = useQueryClient();

  const [name, setName] = useState(user?.name || '');
  const [emailNotifications, setEmailNotifications] = useState(
    user?.settings?.email_notifications ?? true
  );
  const [timezone, setTimezone] = useState(user?.settings?.timezone || 'UTC');

  const updateMutation = useMutation({
    mutationFn: async (data: Partial<UserType>) => {
      return apiClient.put<UserType>('/users/me', data);
    },
    onSuccess: (updatedUser) => {
      updateUser(updatedUser);
      queryClient.invalidateQueries({ queryKey: ['user'] });
      toast.success('Settings saved');
    },
    onError: () => {
      toast.error('Failed to save settings');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.delete<void>('/users/me'),
    onSuccess: () => {
      toast.success('Account deleted');
      logout();
    },
    onError: () => {
      toast.error('Failed to delete account');
    },
  });

  const handleSaveProfile = () => {
    updateMutation.mutate({ name });
  };

  const handleSaveNotifications = () => {
    updateMutation.mutate({
      settings: {
        ...user?.settings,
        email_notifications: emailNotifications,
        timezone,
        meeting_duration: user?.settings?.meeting_duration || 30,
      },
    });
  };

  const handleDeleteAccount = () => {
    if (
      confirm(
        'Are you sure you want to delete your account? This action cannot be undone.'
      )
    ) {
      deleteMutation.mutate();
    }
  };

  const initials = user?.name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase() || 'U';

  return (
    <div className="h-full overflow-y-auto">
      <div className="container mx-auto p-6 max-w-2xl pb-12">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-muted-foreground">Manage your account preferences</p>
        </div>

        <div className="space-y-6">
        {/* Profile Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile
            </CardTitle>
            <CardDescription>Your personal information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16">
                <AvatarImage src={user?.profile_image || undefined} />
                <AvatarFallback className="text-lg">{initials}</AvatarFallback>
              </Avatar>
              <div>
                <p className="font-medium">{user?.name}</p>
                <p className="text-sm text-muted-foreground">{user?.email}</p>
                <Badge variant="outline" className="mt-1">
                  {user?.auth_provider === 'google' ? 'Google Account' : 'Email Account'}
                </Badge>
              </div>
            </div>

            <Separator />

            <div className="space-y-2">
              <Label htmlFor="name">Display Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Current Phase</Label>
              <div className="flex items-center gap-2">
                <Badge variant={user?.phase === 'goal_setting' ? 'default' : 'secondary'}>
                  {user?.phase === 'goal_setting' ? 'Goal Setting' : 'Tracking'}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {user?.phase === 'goal_setting'
                    ? 'Unlimited coach access'
                    : `Meeting every ${user?.meeting_interval} days`}
                </span>
              </div>
            </div>

            <Button
              onClick={handleSaveProfile}
              disabled={updateMutation.isPending || name === user?.name}
            >
              {updateMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              <Save className="mr-2 h-4 w-4" />
              Save Profile
            </Button>
          </CardContent>
        </Card>

        {/* Notifications Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
            <CardDescription>Email and reminder preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label>Email Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Receive meeting reminders and updates via email
                </p>
              </div>
              <Switch
                checked={emailNotifications}
                onCheckedChange={setEmailNotifications}
              />
            </div>

            <Separator />

            <div className="space-y-2">
              <Label>Timezone</Label>
              <Select value={timezone} onValueChange={setTimezone}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="UTC">UTC</SelectItem>
                  <SelectItem value="America/New_York">Eastern Time</SelectItem>
                  <SelectItem value="America/Chicago">Central Time</SelectItem>
                  <SelectItem value="America/Denver">Mountain Time</SelectItem>
                  <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                  <SelectItem value="Europe/London">London</SelectItem>
                  <SelectItem value="Europe/Paris">Paris</SelectItem>
                  <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={handleSaveNotifications}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Save Preferences
            </Button>
          </CardContent>
        </Card>

        {/* Security Section - 2FA */}
        <TwoFactorSetup />

        {/* Danger Zone */}
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <Trash2 className="h-5 w-5" />
              Danger Zone
            </CardTitle>
            <CardDescription>Irreversible account actions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Delete Account</p>
                <p className="text-sm text-muted-foreground">
                  Permanently delete your account and all associated data
                </p>
              </div>
              <Button
                variant="destructive"
                onClick={handleDeleteAccount}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="mr-2 h-4 w-4" />
                )}
                Delete Account
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
      </div>
    </div>
  );
}
