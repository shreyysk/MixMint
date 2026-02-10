'use client';

import { useState, useEffect } from 'react';
import { enrollMFA, verifyMFA, getMFAFactors, unenrollMFA } from '@/lib/auth';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ShieldCheck, ShieldAlert, Key, Loader2, QrCode } from 'lucide-react';
import { Input } from '@/components/ui/Input';

export function MFAManager() {
    const [factors, setFactors] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [enrolling, setEnrolling] = useState(false);
    const [mfaData, setMfaData] = useState<any>(null);
    const [verificationCode, setVerificationCode] = useState('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchFactors();
    }, []);

    async function fetchFactors() {
        setLoading(true);
        try {
            const data = await getMFAFactors();
            setFactors(data.all || []);
        } catch (err: any) {
            setError(err.message);
        }
        setLoading(false);
    }

    async function handleEnroll() {
        setEnrolling(true);
        setError(null);
        try {
            const data = await enrollMFA();
            setMfaData(data);
        } catch (err: any) {
            setError(err.message);
        }
    }

    async function handleVerify() {
        try {
            await verifyMFA(mfaData.id, verificationCode);
            setMfaData(null);
            setVerificationCode('');
            fetchFactors();
        } catch (err: any) {
            setError(err.message);
        }
    }

    async function handleDisable(factorId: string) {
        if (!confirm('Are you sure you want to disable 2FA? This will decrease your account security.')) return;
        try {
            await unenrollMFA(factorId);
            fetchFactors();
        } catch (err: any) {
            setError(err.message);
        }
    }

    const activeFactor = factors.find(f => f.status === 'verified');

    return (
        <Card className="bg-black/40 border-white/10 backdrop-blur-md">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-purple-400" />
                    Two-Factor Authentication (2FA)
                </CardTitle>
                <CardDescription>
                    Add an extra layer of security to your account using an authenticator app.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg flex items-center gap-2">
                        <ShieldAlert className="w-4 h-4" />
                        {error}
                    </div>
                )}

                {activeFactor ? (
                    <div className="flex items-center justify-between p-4 bg-green-500/5 border border-green-500/20 rounded-xl">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-green-500/20 rounded-lg">
                                <Key className="w-5 h-5 text-green-400" />
                            </div>
                            <div>
                                <div className="text-white font-medium">2FA is Enabled</div>
                                <div className="text-xs text-gray-400">Authenticator App (TOTP)</div>
                            </div>
                        </div>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
                            onClick={() => handleDisable(activeFactor.id)}
                        >
                            Disable
                        </Button>
                    </div>
                ) : mfaData ? (
                    <div className="space-y-4 p-4 border border-purple-500/20 rounded-xl bg-purple-500/5">
                        <div className="text-sm text-gray-300">
                            Scan this QR code with your authenticator app (e.g., Google Authenticator, Authy):
                        </div>

                        <div className="flex justify-center bg-white p-2 rounded-lg w-fit mx-auto">
                            {/* In a real app, use a QR code library to render mfaData.totp.qr_code */}
                            <div className="w-32 h-32 bg-gray-100 flex items-center justify-center text-gray-400 text-center text-[10px] p-2">
                                [QR CODE: {mfaData.totp.qr_code.slice(0, 20)}...]
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs text-gray-400">Enter verification code</label>
                            <div className="flex gap-2">
                                <Input
                                    value={verificationCode}
                                    onChange={(e) => setVerificationCode(e.target.value)}
                                    placeholder="000000"
                                    className="text-center tracking-widest font-mono"
                                    maxLength={6}
                                />
                                <Button onClick={handleVerify} disabled={verificationCode.length !== 6}>
                                    Verify
                                </Button>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col items-center py-6 text-center space-y-4">
                        <div className="p-4 bg-gray-500/10 rounded-full">
                            <QrCode className="w-8 h-8 text-gray-400" />
                        </div>
                        <div>
                            <div className="text-white font-medium">Protect your account</div>
                            <div className="text-sm text-gray-500 px-8">
                                Use an authenticator app to generate one-time codes for every login attempt.
                            </div>
                        </div>
                        <Button onClick={handleEnroll} disabled={enrolling}>
                            {enrolling ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                            Setup 2FA
                        </Button>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
