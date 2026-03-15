'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { loansAPI } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { formatCurrency, formatDate, downloadFile } from '@/lib/utils';
import Button from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import {
  ArrowLeft,
  Download,
  Calendar,
  TrendingUp,
  CheckCircle,
  Clock,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function LoanDetailsPage() {
  const router = useRouter();
  const params = useParams();
  const loanId = params?.loanId;
  
  const { isAuthenticated, isAuthInitialized, initAuth } = useAuthStore();
  const [loan, setLoan] = useState(null);
  const [emiSchedule, setEmiSchedule] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  useEffect(() => {
    if (!isAuthInitialized) {
      return;
    }

    if (!isAuthenticated) {
      router.push('/');
      return;
    }

    if (loanId) {
      fetchLoanDetails();
    }
  }, [isAuthenticated, isAuthInitialized, loanId]);

  const fetchLoanDetails = async () => {
    setIsLoading(true);
    try {
      const [loanRes, emiRes] = await Promise.all([
        loansAPI.getLoanDetails(loanId),
        loansAPI.getEMISchedule(loanId),
      ]);
      setLoan(loanRes.data);
      setEmiSchedule(emiRes.data.schedule || []);
    } catch (error) {
      console.error('Failed to fetch loan details:', error);
      toast.error('Failed to load loan details');
      router.push('/dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadSanctionLetter = async () => {
    setIsDownloading(true);
    try {
      const response = await loansAPI.downloadSanctionLetter(loanId);
      downloadFile(response.data, `sanction_letter_${loanId}.pdf`);
      toast.success('Sanction letter downloaded');
    } catch (error) {
      console.error('Download failed:', error);
    } finally {
      setIsDownloading(false);
    }
  };

  if (!isAuthInitialized || !isAuthenticated || isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (!loan) return null;

  const paidEMIs = emiSchedule.filter((emi) => emi.status === 'PAID').length;
  const totalEMIs = emiSchedule.length;
  const progressPercent = totalEMIs > 0 ? (paidEMIs / totalEMIs) * 100 : 0;
  const nextPendingEMI = emiSchedule.find((emi) => emi.status === 'PENDING');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
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
                  {loan.loan_type} Loan Details
                </h1>
                <p className="text-sm text-gray-600">Loan ID: {loan.loan_id}</p>
              </div>
            </div>
            <Button
              onClick={handleDownloadSanctionLetter}
              isLoading={isDownloading}
            >
              <Download className="w-4 h-4 mr-2" />
              Sanction Letter
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Loan Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-gray-600 mb-1">Loan Amount</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(loan.principal)}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Disbursed on {formatDate(loan.disbursement_date)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-gray-600 mb-1">Interest Rate</p>
              <p className="text-2xl font-bold text-gray-900">{loan.interest_rate}%</p>
              <p className="text-xs text-gray-500 mt-1">Per annum</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-gray-600 mb-1">Monthly EMI</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(loan.monthly_emi)}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Next due: {formatDate(nextPendingEMI?.due_date || loan.next_due_date)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-gray-600 mb-1">Tenure</p>
              <p className="text-2xl font-bold text-gray-900">{loan.tenure_months}</p>
              <p className="text-xs text-gray-500 mt-1">Months</p>
            </CardContent>
          </Card>
        </div>

        {/* Repayment Progress */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Repayment Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-gray-600">
                    {paidEMIs} of {totalEMIs} EMIs paid
                  </span>
                  <span className="font-semibold text-gray-900">
                    {progressPercent.toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-gradient-to-r from-primary-500 to-primary-600 h-3 rounded-full transition-all"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-2">
                <div>
                  <p className="text-sm text-gray-600">Total Paid</p>
                  <p className="text-lg font-semibold text-green-600">
                    {formatCurrency(paidEMIs * loan.monthly_emi)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Remaining</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {formatCurrency((totalEMIs - paidEMIs) * loan.monthly_emi)}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* EMI Schedule */}
        <Card>
          <CardHeader>
            <CardTitle>EMI Schedule</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">
                      EMI No.
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">
                      Due Date
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">
                      Principal
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">
                      Interest
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">
                      Total EMI
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-900">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {emiSchedule.map((emi, index) => (
                    <tr
                      key={index}
                      className={`border-b border-gray-100 ${
                        emi.status === 'PAID' ? 'bg-green-50' : ''
                      }`}
                    >
                      <td className="py-3 px-4 text-sm text-gray-900">{emi.month}</td>
                      <td className="py-3 px-4 text-sm text-gray-900">
                        {formatDate(emi.due_date)}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-900 text-right">
                        {formatCurrency(emi.principal_component)}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-900 text-right">
                        {formatCurrency(emi.interest_component)}
                      </td>
                      <td className="py-3 px-4 text-sm font-semibold text-gray-900 text-right">
                        {formatCurrency(emi.emi_amount)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {emi.status === 'PAID' ? (
                          <Badge variant="success" className="inline-flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Paid
                          </Badge>
                        ) : (
                          <Badge variant="warning" className="inline-flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            Pending
                          </Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
