'use client';

import { useState } from 'react';
import { authApi } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Shield, Loader2, CheckCircle, Copy, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import type { TwoFactorSetupResponse } from '@/types';

export function TwoFactorSetup() {
  const { user, setUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [setupData, setSetupData] = useState<TwoFactorSetupResponse | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [showDisableDialog, setShowDisableDialog] = useState(false);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [error, setError] = useState('');

  const is2FAEnabled = user?.two_factor_enabled ?? false;

  const handleSetup = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await authApi.setup2FA();
      setSetupData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to setup 2FA');
      toast.error('Failed to setup 2FA');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      await authApi.verify2FA(verifyCode);
      toast.success('Two-factor authentication enabled!');
      setShowBackupCodes(true);
      // Update user state
      if (user) {
        setUser({ ...user, two_factor_enabled: true });
      }
    } catch (err: any) {
      setError(err.message || 'Invalid code');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisable = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      await authApi.disable2FA(disableCode);
      toast.success('Two-factor authentication disabled');
      setShowDisableDialog(false);
      setDisableCode('');
      // Update user state
      if (user) {
        setUser({ ...user, two_factor_enabled: false });
      }
    } catch (err: any) {
      setError(err.message || 'Invalid code');
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const handleCancel = () => {
    setSetupData(null);
    setVerifyCode('');
    setError('');
  };

  const handleCloseBackupCodes = () => {
    setShowBackupCodes(false);
    setSetupData(null);
    setVerifyCode('');
  };

  // Show backup codes after successful setup
  if (showBackupCodes && setupData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500" />
            Two-Factor Authentication Enabled
          </CardTitle>
          <CardDescription>
            Save these backup codes in a secure location. Each code can only be used once.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-muted p-4 rounded-lg">
            <div className="grid grid-cols-2 gap-2 font-mono text-sm">
              {setupData.backup_codes.map((code, index) => (
                <div key={index} className="flex items-center justify-between bg-background p-2 rounded">
                  <span>{code}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => copyToClipboard(setupData.backup_codes.join('\n'))}
            >
              <Copy className="h-4 w-4 mr-2" />
              Copy All Codes
            </Button>
            <Button className="flex-1" onClick={handleCloseBackupCodes}>
              Done
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center">
            Store these codes safely. You won&apos;t be able to see them again.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Show setup/verify form
  if (setupData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Setup Two-Factor Authentication
          </CardTitle>
          <CardDescription>
            Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* QR Code would be displayed here - using a placeholder since we can't render actual QR */}
          <div className="flex justify-center">
            <div className="bg-white p-4 rounded-lg">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(setupData.qr_code_uri)}`}
                alt="2FA QR Code"
                className="w-48 h-48"
              />
            </div>
          </div>

          <div className="text-center">
            <p className="text-sm text-muted-foreground mb-2">Or enter this code manually:</p>
            <div className="flex items-center justify-center gap-2">
              <code className="bg-muted px-3 py-1 rounded text-sm font-mono">{setupData.secret}</code>
              <Button variant="ghost" size="sm" onClick={() => copyToClipboard(setupData.secret)}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <form onSubmit={handleVerify} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="verifyCode">Enter the 6-digit code from your app</Label>
              <Input
                id="verifyCode"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                placeholder="000000"
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, ''))}
                required
                disabled={isLoading}
                className="text-center text-xl tracking-widest"
              />
            </div>
            {error && (
              <p className="text-sm text-destructive text-center">{error}</p>
            )}
            <div className="flex gap-2">
              <Button type="button" variant="outline" className="flex-1" onClick={handleCancel}>
                Cancel
              </Button>
              <Button type="submit" className="flex-1" disabled={isLoading || verifyCode.length < 6}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  'Enable 2FA'
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    );
  }

  // Default view - show enable/disable button
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Two-Factor Authentication
          </CardTitle>
          <CardDescription>
            Add an extra layer of security to your account by requiring a verification code when you sign in.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {is2FAEnabled ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <CheckCircle className="h-5 w-5" />
                <span className="font-medium">Two-factor authentication is enabled</span>
              </div>
              <Button
                variant="outline"
                onClick={() => setShowDisableDialog(true)}
                className="text-destructive border-destructive hover:bg-destructive/10"
              >
                Disable 2FA
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-muted-foreground">
                <AlertTriangle className="h-5 w-5" />
                <span>Two-factor authentication is not enabled</span>
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button onClick={handleSetup} disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Setting up...
                  </>
                ) : (
                  <>
                    <Shield className="mr-2 h-4 w-4" />
                    Enable 2FA
                  </>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Disable 2FA Dialog */}
      <Dialog open={showDisableDialog} onOpenChange={setShowDisableDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disable Two-Factor Authentication</DialogTitle>
            <DialogDescription>
              Enter your verification code to disable 2FA. This will make your account less secure.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleDisable} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="disableCode">Verification code</Label>
              <Input
                id="disableCode"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                placeholder="000000"
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ''))}
                required
                disabled={isLoading}
                className="text-center text-xl tracking-widest"
              />
              <p className="text-xs text-muted-foreground">
                Enter the code from your authenticator app or a backup code
              </p>
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                onClick={() => {
                  setShowDisableDialog(false);
                  setDisableCode('');
                  setError('');
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="destructive"
                className="flex-1"
                disabled={isLoading || disableCode.length < 6}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Disabling...
                  </>
                ) : (
                  'Disable 2FA'
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
