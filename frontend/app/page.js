'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import toast from 'react-hot-toast';
import { Building2, Shield, Zap, TrendingUp } from 'lucide-react';

export default function Home() {
  const router = useRouter();
  const { setAuth, isAuthenticated, isAuthInitialized, initAuth } = useAuthStore();
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [isOTPSent, setIsOTPSent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Initialize auth from localStorage on mount
  useEffect(() => {
    initAuth();
  }, [initAuth]);

  useEffect(() => {
    if (isAuthInitialized && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, isAuthInitialized, router]);

  const handleRequestOTP = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await authAPI.requestOTP(email);
      toast.success(response.data.message || 'OTP sent to your email');
      setIsOTPSent(true);
    } catch (error) {
      console.error('OTP request failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await authAPI.verifyOTP(email, otp);
      const { access_token, user } = response.data;
      setAuth(user, access_token);
      toast.success('Login successful!');
      router.push('/dashboard');
    } catch (error) {
      console.error('OTP verification failed:', error);
      setOtp('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-2">
            <Building2 className="w-8 h-8 text-primary-600" />
            <h1 className="text-2xl font-bold text-gray-900">NBFC Loan Platform</h1>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Hero Section */}
          <div className="space-y-8 animate-fade-in">
            <div>
              <h2 className="text-4xl font-bold text-gray-900 mb-4">
                Smart Loans, Instant Decisions
              </h2>
              <p className="text-xl text-gray-600">
                Experience AI-powered loan processing with conversational applications and instant credit decisions.
              </p>
            </div>

            {/* Features */}
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Instant Processing</h3>
                  <p className="text-gray-600">Get loan decisions in minutes, not days</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                  <Shield className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Secure & Compliant</h3>
                  <p className="text-gray-600">Bank-grade security and RBI compliance</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Competitive Rates</h3>
                  <p className="text-gray-600">Best rates based on your credit profile</p>
                </div>
              </div>
            </div>
          </div>

          {/* Login Card */}
          <div className="animate-slide-up">
            <Card className="shadow-xl">
              <CardHeader>
                <CardTitle>
                  {isOTPSent ? 'Verify OTP' : 'Get Started'}
                </CardTitle>
                <p className="text-sm text-gray-600 mt-1">
                  {isOTPSent
                    ? `We sent a 6-digit code to ${email}`
                    : 'Enter your email to receive a one-time password'}
                </p>
              </CardHeader>
              <CardContent>
                {!isOTPSent ? (
                  <form onSubmit={handleRequestOTP} className="space-y-4">
                    <Input
                      type="email"
                      label="Email Address"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                    <Button
                      type="submit"
                      className="w-full"
                      isLoading={isLoading}
                    >
                      Send OTP
                    </Button>
                  </form>
                ) : (
                  <form onSubmit={handleVerifyOTP} className="space-y-4">
                    <Input
                      type="text"
                      label="6-Digit OTP"
                      placeholder="000000"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      maxLength={6}
                      required
                    />
                    <Button
                      type="submit"
                      className="w-full"
                      isLoading={isLoading}
                      disabled={otp.length !== 6}
                    >
                      Verify & Login
                    </Button>
                    <button
                      type="button"
                      onClick={() => {
                        setIsOTPSent(false);
                        setOtp('');
                      }}
                      className="w-full text-sm text-primary-600 hover:text-primary-700"
                    >
                      Change email address
                    </button>
                  </form>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
