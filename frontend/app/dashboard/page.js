'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { loansAPI } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import { formatCurrency, formatDate, getStatusColor } from '@/lib/utils';
import Button from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import {
  Building2,
  Plus,
  CreditCard,
  TrendingUp,
  Calendar,
  LogOut,
  Briefcase,
  Home,
  ShoppingCart,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function Dashboard() {
  const router = useRouter();
  const { user, clearAuth, isAuthenticated } = useAuthStore();
  const [activeLoans, setActiveLoans] = useState([]);
  const [applications, setApplications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/');
      return;
    }
    fetchData();
  }, [isAuthenticated]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [loansRes, appsRes] = await Promise.all([
        loansAPI.getActiveLoans(),
        loansAPI.getApplications(),
      ]);
      setActiveLoans(loansRes.data.loans || []);
      setApplications(appsRes.data.applications || []);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    clearAuth();
    toast.success('Logged out successfully');
    router.push('/');
  };

  const loanTypes = [
    {
      type: 'personal',
      title: 'Personal Loan',
      icon: Briefcase,
      description: 'Quick funds for personal needs',
      color: 'text-blue-600 bg-blue-100',
    },
    {
      type: 'home',
      title: 'Home Loan',
      icon: Home,
      description: 'Finance your dream home',
      color: 'text-green-600 bg-green-100',
    },
    {
      type: 'business',
      title: 'Business Loan',
      icon: ShoppingCart,
      description: 'Grow your business',
      color: 'text-purple-600 bg-purple-100',
    },
  ];

  const stats = {
    activeLoans: activeLoans.length,
    totalBorrowed: activeLoans.reduce((sum, loan) => sum + (loan.approved_amount || 0), 0),
    nextEMI: activeLoans[0]?.next_emi_amount || 0,
    pendingApplications: applications.filter((app) => app.status === 'in_progress').length,
  };

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="w-8 h-8 text-primary-600" />
              <h1 className="text-2xl font-bold text-gray-900">NBFC Loan Platform</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">{user?.email}</p>
                <p className="text-xs text-gray-500">Customer</p>
              </div>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Active Loans</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.activeLoans}</p>
                </div>
                <CreditCard className="w-10 h-10 text-primary-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Borrowed</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatCurrency(stats.totalBorrowed)}
                  </p>
                </div>
                <TrendingUp className="w-10 h-10 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Next EMI</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatCurrency(stats.nextEMI)}
                  </p>
                </div>
                <Calendar className="w-10 h-10 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Pending Applications</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.pendingApplications}</p>
                </div>
                <Briefcase className="w-10 h-10 text-blue-600" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Apply for Loan */}
        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Apply for a New Loan</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {loanTypes.map((loanType) => {
              const Icon = loanType.icon;
              return (
                <Card
                  key={loanType.type}
                  className="cursor-pointer hover:shadow-lg transition-shadow"
                  onClick={() => router.push(`/apply/${loanType.type}`)}
                >
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className={`w-12 h-12 rounded-lg ${loanType.color} flex items-center justify-center`}>
                        <Icon className="w-6 h-6" />
                      </div>
                      <Plus className="w-5 h-5 text-gray-400" />
                    </div>
                    <h3 className="font-semibold text-gray-900 mb-1">{loanType.title}</h3>
                    <p className="text-sm text-gray-600">{loanType.description}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>

        {/* Active Loans */}
        {activeLoans.length > 0 && (
          <section className="mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Active Loans</h2>
            <div className="space-y-4">
              {activeLoans.map((loan) => (
                <Card
                  key={loan.loan_id}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => router.push(`/loans/${loan.loan_id}`)}
                >
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-gray-900 capitalize">
                            {loan.loan_type} Loan
                          </h3>
                          <Badge variant="success">Active</Badge>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <p className="text-gray-600">Amount</p>
                            <p className="font-medium text-gray-900">
                              {formatCurrency(loan.approved_amount)}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-600">Interest Rate</p>
                            <p className="font-medium text-gray-900">{loan.interest_rate}% p.a.</p>
                          </div>
                          <div>
                            <p className="text-gray-600">EMI</p>
                            <p className="font-medium text-gray-900">
                              {formatCurrency(loan.monthly_emi)}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-600">Next Due</p>
                            <p className="font-medium text-gray-900">
                              {formatDate(loan.next_emi_date)}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {/* Recent Applications */}
        {applications.length > 0 && (
          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Applications</h2>
            <div className="space-y-4">
              {applications.slice(0, 5).map((app) => (
                <Card
                  key={app.application_id}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => router.push(`/apply/${app.loan_type}`)}
                >
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-gray-900 capitalize mb-1">
                          {app.loan_type} Loan Application
                        </h3>
                        <p className="text-sm text-gray-600">
                          Applied on {formatDate(app.created_at)}
                        </p>
                      </div>
                      <Badge className={getStatusColor(app.status)}>
                        {app.status.replace('_', ' ')}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {isLoading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto" />
          </div>
        )}
      </main>
    </div>
  );
}
