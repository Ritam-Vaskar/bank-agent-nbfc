'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { loansAPI } from '@/lib/api';
import { useAuthStore, useApplicationStore } from '@/lib/store';
import { formatCurrency } from '@/lib/utils';
import ChatInterface from '@/components/chat/ChatInterface';
import Button from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import {
  ArrowLeft, CheckCircle, Circle, Loader, MessageSquare,
  FileText, ShieldCheck, CreditCard, BarChart2, Percent,
  AlertCircle, TrendingUp, Award
} from 'lucide-react';
import toast from 'react-hot-toast';

// Ordered list of all agent pipeline stages
const AGENT_STEPS = [
  {
    id: 'collect',
    label: 'Application Details',
    description: 'Collecting KYC & loan requirements',
    icon: FileText,
    stages: ['init', 'collect_info'],
  },
  {
    id: 'kyc',
    label: 'KYC Verification',
    description: 'Mock UIDAI Aadhaar & PAN check',
    icon: ShieldCheck,
    stages: ['verify_kyc'],
  },
  {
    id: 'credit',
    label: 'Credit Bureau Check',
    description: 'Mock CIBIL credit report fetch',
    icon: CreditCard,
    stages: ['fetch_credit'],
  },
  {
    id: 'policy',
    label: 'Policy Validation',
    description: 'Eligibility rules & loan limits',
    icon: AlertCircle,
    stages: ['check_policy'],
  },
  {
    id: 'affordability',
    label: 'Affordability Analysis',
    description: 'FOIR computation & eligible amount',
    icon: Percent,
    stages: ['assess_affordability'],
  },
  {
    id: 'risk',
    label: 'Risk Scoring',
    description: 'Weighted 5-factor risk model',
    icon: BarChart2,
    stages: ['assess_risk'],
  },
  {
    id: 'offer',
    label: 'Offer Generation',
    description: 'Pricing, EMI & approval decision',
    icon: TrendingUp,
    stages: ['generate_offer', 'explain_offer', 'await_acceptance'],
  },
  {
    id: 'sanction',
    label: 'Sanction & Disbursement',
    description: 'PDF letter generation & loan creation',
    icon: Award,
    stages: ['generate_sanction', 'simulate_disbursement', 'completed'],
  },
];

// Returns the index of the step that owns `stage`
function resolveStepIndex(stage) {
  if (!stage) return 0;
  const idx = AGENT_STEPS.findIndex((s) => s.stages.includes(stage));
  return idx === -1 ? 0 : idx;
}

function getProgressStepState(workflowStage, isRejected, progress) {
  if (!progress) {
    const stageIndex = resolveStepIndex(workflowStage);
    const doneByStage = AGENT_STEPS.map((_, index) => index < stageIndex);

    if (workflowStage === 'await_acceptance') {
      doneByStage[6] = true;
    }

    if (workflowStage === 'completed' && !isRejected) {
      for (let index = 0; index < doneByStage.length; index++) {
        doneByStage[index] = true;
      }
    }

    return {
      doneByProgress: doneByStage,
      currentIndex: isRejected ? stageIndex : Math.min(stageIndex, AGENT_STEPS.length - 1),
      rejectedIndex: isRejected ? stageIndex : -1,
    };
  }

  const doneByProgress = [
    false,
    !!progress?.kyc_done,
    !!progress?.credit_done,
    !!progress?.policy_done,
    !!progress?.affordability_done,
    !!progress?.risk_done,
    !!progress?.offer_done,
    !!progress?.sanction_done,
  ];

  const allDone = doneByProgress.every((value) => value === true);
  const firstPending = doneByProgress.findIndex((value) => !value);

  let currentIndex = 0;
  if (workflowStage === 'await_acceptance') {
    currentIndex = 6;
  } else if (workflowStage === 'generate_sanction' || workflowStage === 'simulate_disbursement') {
    currentIndex = 7;
  } else if (workflowStage === 'completed' && allDone) {
    currentIndex = 7;
  } else if (firstPending !== -1) {
    currentIndex = firstPending;
  } else {
    currentIndex = resolveStepIndex(workflowStage);
  }

  let rejectedIndex = -1;
  if (isRejected) {
    if (!progress?.kyc_done) rejectedIndex = 1;
    else if (!progress?.credit_done) rejectedIndex = 2;
    else if (!progress?.policy_done) rejectedIndex = 3;
    else if (!progress?.affordability_done) rejectedIndex = 4;
    else if (!progress?.risk_done) rejectedIndex = 5;
    else if (!progress?.offer_done) rejectedIndex = 6;
    else rejectedIndex = 7;
  }

  return {
    doneByProgress,
    currentIndex,
    rejectedIndex,
  };
}

export default function ApplyPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const loanType = params?.loanType || 'personal';
  const requestedApplicationId = searchParams.get('applicationId');

  const { isAuthenticated, isAuthInitialized, initAuth } = useAuthStore();
  const {
    currentApplicationId,
    currentLoanType,
    messages,
    workflowStage,
    applicationStatus,
    pipelineProgress,
    loanOffer,
    loanId,
    isCompleted,
    isLoading,
    setCurrentApplication,
    addMessage,
    setApplicationSnapshot,
    setLoading,
    clearMessages,
  } = useApplicationStore();

  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => { initAuth(); }, [initAuth]);

  useEffect(() => {
    if (!isAuthInitialized) return;
    if (!isAuthenticated) { router.push('/'); return; }
    initializeApplication();
  }, [isAuthenticated, isAuthInitialized, loanType, requestedApplicationId]);

  const initializeApplication = async () => {
    setIsInitializing(true);
    try {
      const appIdToResume =
        requestedApplicationId ||
        (!isCompleted && currentLoanType === loanType ? currentApplicationId : null);

      if (appIdToResume) {
        const resumed = await hydrateApplication(appIdToResume);
        if (resumed) return;
      }

      const applicationsResponse = await loansAPI.getApplications();
      const match = (applicationsResponse.data.applications || []).find(
        (a) => a.loan_type === loanType && a.status === 'IN_PROGRESS'
      );
      if (match?.application_id) {
        const resumed = await hydrateApplication(match.application_id);
        if (resumed) return;
      }

      clearMessages();
      const response = await loansAPI.applyForLoan(loanType);
      const { application_id, messages: backendMessages } = response.data;
      setCurrentApplication(application_id, loanType);
      setApplicationSnapshot({
        applicationId: application_id,
        loanType,
        messages: (backendMessages || []).map((m) => ({
          ...m,
          timestamp: m.timestamp || new Date().toISOString(),
        })),
        stage: response.data.stage,
        status: response.data.status,
        progress: response.data.progress,
        loanOffer: null,
        loanId: null,
        isCompleted: false,
      });
    } catch (error) {
      console.error('Failed to initialize application:', error);
      toast.error('Failed to start application');
      router.push('/dashboard');
    } finally {
      setIsInitializing(false);
    }
  };

  const hydrateApplication = async (applicationId) => {
    try {
      const response = await loansAPI.getApplication(applicationId);
      const application = response.data;
      setApplicationSnapshot({
        applicationId: application.application_id,
        loanType: application.loan_type,
        messages: (application.conversation_messages || []).map((m) => ({
          ...m,
          timestamp: m.timestamp || new Date().toISOString(),
        })),
        stage: application.workflow_stage,
        status: application.status,
        progress: application.progress || null,
        loanOffer: application.loan_offer || null,
        loanId: application.loan_id || null,
        isCompleted: ['completed', 'rejected'].includes(application.workflow_stage),
      });
      return true;
    } catch {
      return false;
    }
  };

  const handleSendMessage = async (message) => {
    if (!currentApplicationId) {
      toast.error('Application is still loading. Please try again.');
      return;
    }
    addMessage({ role: 'user', content: message, timestamp: new Date().toISOString() });
    setLoading(true);
    try {
      const response = await loansAPI.sendMessage(currentApplicationId, message);
      const { messages: backendMessages, stage, status, progress, loan_offer, loan_id, completed } = response.data;
      setApplicationSnapshot({
        applicationId: currentApplicationId,
        loanType,
        messages: (backendMessages || []).map((m) => ({
          ...m,
          timestamp: m.timestamp || new Date().toISOString(),
        })),
        stage,
        status,
        progress,
        loanOffer: loan_offer || loanOffer,
        loanId: loan_id || loanId,
        isCompleted: completed,
      });
      if (!isCompleted && completed && loan_id) {
        toast.success('Loan sanctioned! Sanction letter is ready.');
      }
    } catch (error) {
      let errorText = 'Sorry, something went wrong. Please try again.';
      if (error.response?.data?.detail) {
        errorText =
          typeof error.response.data.detail === 'string'
            ? error.response.data.detail
            : Array.isArray(error.response.data.detail)
            ? error.response.data.detail.map((e) => e.msg).join(', ')
            : errorText;
      }
      addMessage({ role: 'assistant', content: errorText, timestamp: new Date().toISOString() });
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptOffer = async () => {
    await handleSendMessage('I accept this loan offer and would like to proceed.');
  };

  const handleRejectOffer = async () => {
    await handleSendMessage('I do not want to proceed with this loan offer.');
  };

  const isRejected = applicationStatus === 'DECLINED' || workflowStage === 'rejected';
  const isProcessComplete = isCompleted || workflowStage === 'completed' || isRejected;
  const showOfferActions = loanOffer && workflowStage === 'await_acceptance' && !isLoading;
  const {
    doneByProgress,
    currentIndex: currentStepIndex,
    rejectedIndex,
  } = getProgressStepState(workflowStage, isRejected, pipelineProgress);

  // Derive nice loan type label
  const loanLabel = loanType
    .replace('_loan', '')
    .replace('_', ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

  if (!isAuthInitialized || !isAuthenticated) return null;

  if (isInitializing) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
          <p className="text-sm text-gray-600">Initialising loan agent…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => router.push('/dashboard')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                {loanLabel} Loan Application
              </h1>
              <p className="text-sm text-gray-500">
                ID: {currentApplicationId?.slice(0, 8) || '—'}
                {workflowStage && (
                  <span className="ml-2 text-primary-600 font-medium capitalize">
                    · {workflowStage.replace(/_/g, ' ')}
                  </span>
                )}
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 min-h-0 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid lg:grid-cols-3 gap-6 h-full min-h-0">

          {/* ── Sidebar ── */}
          <div className="lg:col-span-1 space-y-4 lg:h-full lg:overflow-y-auto pr-1">

            {/* Agent Pipeline Progress */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                  Agent Pipeline
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-1">
                  {AGENT_STEPS.map((step, index) => {
                    const StepIcon = step.icon;
                    const isDone = doneByProgress[index];
                    const isCurrent = !isProcessComplete && index === currentStepIndex;
                    const isRejectedStep = isRejected && index === rejectedIndex;

                    return (
                      <div key={step.id} className="flex items-start gap-3 py-2">
                        {/* Status icon */}
                        <div className="flex-shrink-0 mt-0.5">
                          {isRejectedStep ? (
                            <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center">
                              <AlertCircle className="w-4 h-4 text-red-500" />
                            </div>
                          ) : isDone ? (
                            <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                              <CheckCircle className="w-4 h-4 text-green-600" />
                            </div>
                          ) : isCurrent ? (
                            <div className="w-6 h-6 rounded-full bg-primary-100 flex items-center justify-center">
                              <Loader className="w-4 h-4 text-primary-600 animate-spin" />
                            </div>
                          ) : (
                            <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                              <StepIcon className="w-3.5 h-3.5 text-gray-400" />
                            </div>
                          )}
                        </div>
                        {/* Label */}
                        <div className="min-w-0">
                          <p
                            className={`text-sm font-medium leading-tight ${
                              isDone
                                ? 'text-green-700'
                                : isCurrent
                                ? 'text-primary-700'
                                : isRejectedStep
                                ? 'text-red-600'
                                : 'text-gray-400'
                            }`}
                          >
                            {step.label}
                          </p>
                          {(isCurrent || isDone) && (
                            <p className="text-xs text-gray-500 mt-0.5 leading-tight">
                              {step.description}
                            </p>
                          )}
                        </div>
                        {/* Badge for current step */}
                        {isCurrent && !isLoading && (
                          <span className="flex-shrink-0 ml-auto text-xs bg-primary-100 text-primary-700 rounded px-1.5 py-0.5">
                            Active
                          </span>
                        )}
                        {isCurrent && isLoading && (
                          <span className="flex-shrink-0 ml-auto text-xs bg-yellow-100 text-yellow-700 rounded px-1.5 py-0.5">
                            Running
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Completion card */}
            {isProcessComplete && (
              <Card
                className={
                  isRejected
                    ? 'border-red-200 bg-red-50'
                    : 'border-green-200 bg-green-50'
                }
              >
                <CardContent className="pt-5 space-y-3">
                  <div className="flex items-start gap-3">
                    {isRejected ? (
                      <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                    ) : (
                      <MessageSquare className="w-5 h-5 text-green-700 mt-0.5 flex-shrink-0" />
                    )}
                    <div>
                      <p
                        className={`font-semibold ${
                          isRejected ? 'text-red-800' : 'text-green-900'
                        }`}
                      >
                        {isRejected ? 'Application not approved' : 'Conversation saved'}
                      </p>
                      <p
                        className={`text-sm mt-0.5 ${
                          isRejected ? 'text-red-700' : 'text-green-800'
                        }`}
                      >
                        {isRejected
                          ? 'You can ask follow-up questions below or start a new application.'
                          : 'You can return anytime and ask follow-up questions.'}
                      </p>
                    </div>
                  </div>
                  {loanId && !isRejected && (
                    <Button
                      className="w-full"
                      onClick={() => router.push(`/loans/${loanId}`)}
                    >
                      <FileText className="w-4 h-4 mr-2" />
                      View Loan & Download Letter
                    </Button>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Loan Offer card */}
            {loanOffer && (
              <Card className="border-primary-200 bg-primary-50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-primary-900 flex items-center gap-2">
                    <Award className="w-4 h-4" />
                    Loan Offer
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="text-xs text-primary-600 uppercase tracking-wide">Approved Amount</p>
                    <p className="text-2xl font-bold text-primary-900">
                      {formatCurrency(loanOffer.principal)}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-white/60 rounded p-2">
                      <p className="text-xs text-primary-600">Interest Rate</p>
                      <p className="font-semibold text-primary-900">
                        {loanOffer.interest_rate}% p.a.
                      </p>
                    </div>
                    <div className="bg-white/60 rounded p-2">
                      <p className="text-xs text-primary-600">Tenure</p>
                      <p className="font-semibold text-primary-900">
                        {loanOffer.tenure_months} months
                      </p>
                    </div>
                    <div className="bg-white/60 rounded p-2">
                      <p className="text-xs text-primary-600">Monthly EMI</p>
                      <p className="font-semibold text-primary-900">
                        {formatCurrency(loanOffer.monthly_emi)}
                      </p>
                    </div>
                    <div className="bg-white/60 rounded p-2">
                      <p className="text-xs text-primary-600">Risk Segment</p>
                      <p className="font-semibold text-primary-900">
                        {loanOffer.risk_segment}
                      </p>
                    </div>
                  </div>
                  <div className="bg-white/60 rounded p-2 text-sm">
                    <p className="text-xs text-primary-600">Net Disbursement</p>
                    <p className="font-semibold text-primary-900">
                      {formatCurrency(loanOffer.net_disbursement)}
                    </p>
                  </div>
                  {showOfferActions && (
                    <div className="space-y-2 pt-1">
                      <Button onClick={handleAcceptOffer} className="w-full" isLoading={isLoading}>
                        Accept Offer
                      </Button>
                      <Button
                        variant="outline"
                        onClick={handleRejectOffer}
                        className="w-full"
                        isLoading={isLoading}
                      >
                        Reject Offer
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* How it works */}
            {!isProcessComplete && !loanOffer && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">How it works</CardTitle>
                </CardHeader>
                <CardContent>
                  <ol className="space-y-2 text-sm text-gray-600">
                    <li className="flex gap-2">
                      <span className="font-semibold text-primary-600">1.</span>
                      <span>Provide KYC details (Aadhaar, PAN) and loan requirement</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-semibold text-primary-600">2.</span>
                      <span>Agents verify identity via mock UIDAI, fetch credit via mock CIBIL</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-semibold text-primary-600">3.</span>
                      <span>Affordability & risk scoring runs automatically</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="font-semibold text-primary-600">4.</span>
                      <span>Accept the offer to get your sanction letter PDF</span>
                    </li>
                  </ol>
                  <p className="mt-3 text-xs text-gray-400">
                    Tip: type <code className="bg-gray-100 px-1 rounded">demo</code> to auto-fill sample data and run the full flow instantly.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* ── Chat Interface ── */}
          <Card className="lg:col-span-2 flex flex-col h-screen overflow-hidden">
            <CardHeader className="flex-shrink-0 border-b pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-primary-600" />
                  Loan Agent Chat
                </CardTitle>
                <Badge variant={isRejected ? 'danger' : isProcessComplete ? 'success' : 'info'}>
                  {isRejected
                    ? 'Application Closed'
                    : isProcessComplete
                    ? 'Completed'
                    : isLoading
                    ? 'Agent thinking…'
                    : 'AI Powered'}
                </Badge>
              </div>
            </CardHeader>
            <div className="flex-1 min-h-0 overflow-y-auto">
              <ChatInterface
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                isConversationComplete={isProcessComplete}
              />
            </div>
          </Card>

        </div>
      </div>
    </div>
  );
}
