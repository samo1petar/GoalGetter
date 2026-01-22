'use client';

import { useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { useChatStore } from '@/stores/chatStore';
import { authApi, type SignupRequest, type LoginRequest } from '@/lib/api/auth';
import { toast } from 'sonner';

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const {
    user,
    isAuthenticated,
    isLoading,
    setTokens,
    setUser,
    logout: logoutStore,
  } = useAuthStore();
  const { clearMessages } = useChatStore();

  // Fetch current user
  const { data: userData, refetch: refetchUser } = useQuery({
    queryKey: ['user', 'me'],
    queryFn: authApi.getMe,
    enabled: isAuthenticated,
  });

  // Update user when data is fetched
  useEffect(() => {
    if (userData) {
      setUser(userData);
    }
  }, [userData, setUser]);

  // Signup mutation
  const signupMutation = useMutation({
    mutationFn: (data: SignupRequest) => authApi.signup(data),
    onSuccess: (response) => {
      setTokens(response.access_token, response.refresh_token);
      setUser(response.user);
      toast.success('Account created successfully!');
      router.push('/app');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Signup failed');
    },
  });

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (response) => {
      // Check if 2FA is required
      if ('requires_2fa' in response && response.requires_2fa) {
        // 2FA required - don't navigate, let the login page handle it
        toast.info('Two-factor authentication required');
        return;
      }
      // Type guard: response is AuthResponse
      if ('access_token' in response) {
        setTokens(response.access_token, response.refresh_token);
        setUser(response.user);
        toast.success('Welcome back!');
        router.push('/app');
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Invalid credentials');
    },
  });

  // Logout
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore errors on logout
    }
    // Clear chat messages to prevent data leakage to next user
    clearMessages();
    // Clear all user-specific caches to prevent data leakage
    queryClient.removeQueries({ queryKey: ['chat'] });
    queryClient.removeQueries({ queryKey: ['goals'] });
    queryClient.removeQueries({ queryKey: ['goal'] });
    logoutStore();
    router.push('/login');
    toast.success('Logged out successfully');
  }, [logoutStore, clearMessages, queryClient, router]);

  // Google OAuth
  const loginWithGoogle = useCallback(() => {
    window.location.href = authApi.getGoogleAuthUrl();
  }, []);

  return {
    user,
    isAuthenticated,
    isLoading,
    signup: signupMutation.mutate,
    login: loginMutation.mutate,
    logout,
    loginWithGoogle,
    isSigningUp: signupMutation.isPending,
    isLoggingIn: loginMutation.isPending,
    refetchUser,
  };
}
