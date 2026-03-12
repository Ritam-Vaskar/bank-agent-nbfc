'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { loansAPI } from '@/lib/api';
import { useAuthStore, useApplicationStore } from '@/lib/store';
import { formatCurrency } from '@/lib/utils';
import ChatInterface from '@/components/chat/ChatInterface';
import Button from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import { ArrowLeft, CheckCircle, Circle, Loader } from 'lucide-react';
import toast from 'react-hot-toast';

export default function ApplyPage() {
  const router = useRouter();
  const params = useParams();
  const loanType = params?.loanType || 'personal';
  
  const { isAuthenticated, initAuth } = useAuthStore();
  const {
    currentApplicationId,
    messages,
    isLoading,
    setCurrentApplication,
    addMessage,
    setMessages,
    setLoading,
  } = useApplicationStore();

  const [loanOffer, setLoanOffer] = useState(null);

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/');
      return;
    }
    initializeApplication();
  }, [isAuthenticated, loanType]);

  const initializeApplication = async () => {
    try {
      const response = await loansAPI.applyForLoan(loanType);
      const { application_id, messages: backendMessages } = response.data;
      setCurrentApplication(application_id);
      
      // Convert backend messages to frontend format
      const formattedMessages = backendMessages.map(msg => ({
        ...msg,
        timestamp: msg.timestamp || new Date().toISOString(),
      }));
      
      setMessages(formattedMessages);
    } catch (error) {
      console.error('Failed to initialize application:', error);
      toast.error('Failed to start application');
      router.push('/dashboard');
    }
  };

  const handleSendMessage = async (message) => {
    // Add user message
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    addMessage(userMessage);
    setLoading(true);

    try {
      const response = await loansAPI.sendMessage(currentApplicationId, message);
      const { messages: backendMessages, stage, loan_offer, completed } = response.data;

      // Update all messages from backend (includes both user and assistant messages)
      const formattedMessages = backendMessages.map(msg => ({
        ...msg,
        timestamp: msg.timestamp || new Date().toISOString(),
      }));
      
      setMessages(formattedMessages);

      // Check if loan offer is generated
      if (loan_offer) {
        setLoanOffer(loan_offer);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Extract error message
      let errorText = 'Sorry, something went wrong. Please try again.';
      if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === 'string') {
          errorText = error.response.data.detail;
        } else if (Array.isArray(error.response.data.detail)) {
          // Handle FastAPI validation errors
          errorText = error.response.data.detail.map(err => err.msg).join(', ');
        }
      }
      
      const errorMessage = {
        role: 'assistant',
        content: errorText,
        timestamp: new Date().toISOString(),
      };
      addMessage(errorMessage);
      toast.error(errorText);
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptOffer = async () => {
    toast.success('Loan offer accepted! Redirecting to dashboard...');
    setTimeout(() => router.push('/dashboard'), 2000);
  };

  const handleRejectOffer = () => {
    toast.error('Loan offer rejected');
    router.push('/dashboard');
  };

  const workflowSteps = [
    { id: 'kyc', label: 'KYC Verification' },
    { id: 'credit', label: 'Credit Check' },
    { id: 'risk', label: 'Risk Assessment' },
    { id: 'offer', label: 'Loan Offer' },
  ];

  const currentStepIndex = messages.length > 0 ? Math.min(Math.floor(messages.length / 3), 3) : 0;

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push('/dashboard')}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-xl font-bold text-gray-900 capitalize">
                {loanType} Loan Application
              </h1>
              <p className="text-sm text-gray-600">
                Application ID: {currentApplicationId?.slice(0, 8)}
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid lg:grid-cols-3 gap-6 h-full">
          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            {/* Workflow Progress */}
            <Card>
              <CardHeader>
                <CardTitle>Application Progress</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {workflowSteps.map((step, index) => {
                    const isCompleted = index < currentStepIndex;
                    const isCurrent = index === currentStepIndex;
                    
                    return (
                      <div key={step.id} className="flex items-center gap-3">
                        {isCompleted ? (
                          <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0" />
                        ) : isCurrent ? (
                          <Loader className="w-6 h-6 text-primary-600 animate-spin flex-shrink-0" />
                        ) : (
                          <Circle className="w-6 h-6 text-gray-300 flex-shrink-0" />
                        )}
                        <span
                          className={`text-sm ${
                            isCompleted || isCurrent
                              ? 'text-gray-900 font-medium'
                              : 'text-gray-500'
                          }`}
                        >
                          {step.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Loan Offer */}
            {loanOffer && (
              <Card className="border-primary-200 bg-primary-50">
                <CardHeader>
                  <CardTitle className="text-primary-900">Loan Offer Generated!</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-sm text-primary-700">Approved Amount</p>
                    <p className="text-2xl font-bold text-primary-900">
                      {formatCurrency(loanOffer.approved_amount)}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-primary-700">Interest Rate</p>
                      <p className="font-semibold text-primary-900">
                        {loanOffer.interest_rate}% p.a.
                      </p>
                    </div>
                    <div>
                      <p className="text-primary-700">Tenure</p>
                      <p className="font-semibold text-primary-900">
                        {loanOffer.tenure_months} months
                      </p>
                    </div>
                    <div>
                      <p className="text-primary-700">Monthly EMI</p>
                      <p className="font-semibold text-primary-900">
                        {formatCurrency(loanOffer.monthly_emi)}
                      </p>
                    </div>
                    <div>
                      <p className="text-primary-700">Risk Score</p>
                      <p className="font-semibold text-primary-900">{loanOffer.risk_score}</p>
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 pt-2">
                    <Button onClick={handleAcceptOffer} className="w-full">
                      Accept Offer
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleRejectOffer}
                      className="w-full"
                    >
                      Reject Offer
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Instructions */}
            <Card>
              <CardHeader>
                <CardTitle>How it works</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-2 text-sm text-gray-600">
                  <li className="flex gap-2">
                    <span className="font-semibold text-primary-600">1.</span>
                    <span>Answer questions about your loan requirement</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-semibold text-primary-600">2.</span>
                    <span>Provide KYC and financial information</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-semibold text-primary-600">3.</span>
                    <span>Our AI agent will process your application</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-semibold text-primary-600">4.</span>
                    <span>Get instant loan offer and accept it</span>
                  </li>
                </ol>
              </CardContent>
            </Card>
          </div>

          {/* Chat Interface */}
          <Card className="lg:col-span-2 flex flex-col" style={{ height: 'calc(100vh - 200px)' }}>
            <CardHeader className="flex-shrink-0">
              <div className="flex items-center justify-between">
                <CardTitle>Chat with Loan Agent</CardTitle>
                <Badge variant="info">AI Powered</Badge>
              </div>
            </CardHeader>
            <div className="flex-1 min-h-0">
              <ChatInterface
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
              />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
