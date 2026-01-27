'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  MessageSquare,
  CreditCard,
  FileText,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  PlusCircle,
} from 'lucide-react'
import Navbar from '@/components/Navbar'
import axios from 'axios'

export default function Dashboard() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin')
    } else if (status === 'authenticated') {
      fetchApplications()
    }
  }, [status, router])

  const fetchApplications = async () => {
    try {
      const response = await axios.get('/api/backend/loans/user', {
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      })
      setApplications(response.data.loans || [])
    } catch (error) {
      console.error('Failed to fetch applications:', error)
    } finally {
      setLoading(false)
    }
  }

  if (status === 'loading' || loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar />
      
      <div className="container mx-auto px-4 py-8">
        {/* Welcome Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold mb-2">
            Welcome back, {session?.user?.name}!
          </h1>
          <p className="text-gray-600 dark:text-gray-300">
            Manage your loan applications and start new ones
          </p>
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid md:grid-cols-4 gap-4 mb-8"
        >
          <QuickActionCard
            icon={<PlusCircle className="w-6 h-6" />}
            title="New Loan"
            description="Start application"
            onClick={() => router.push('/chat')}
            color="bg-blue-600"
          />
          <QuickActionCard
            icon={<MessageSquare className="w-6 h-6" />}
            title="Chat"
            description="Get assistance"
            onClick={() => router.push('/chat')}
            color="bg-green-600"
          />
          <QuickActionCard
            icon={<FileText className="w-6 h-6" />}
            title="Documents"
            description="Upload docs"
            onClick={() => {}}
            color="bg-purple-600"
          />
          <QuickActionCard
            icon={<CreditCard className="w-6 h-6" />}
            title="Credit Score"
            description="Check score"
            onClick={() => {}}
            color="bg-orange-600"
          />
        </motion.div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="grid md:grid-cols-3 gap-6 mb-8"
        >
          <StatCard
            title="Active Applications"
            value={applications.filter((a) => a.state !== 'COMPLETE').length}
            icon={<Clock className="w-8 h-8 text-blue-600" />}
            trend="+2 this month"
          />
          <StatCard
            title="Approved Loans"
            value={applications.filter((a) => a.state === 'COMPLETE').length}
            icon={<CheckCircle className="w-8 h-8 text-green-600" />}
            trend="100% approval"
          />
          <StatCard
            title="Total Sanctioned"
            value={`₹${applications
              .filter((a) => a.data?.approved_amount)
              .reduce((sum, a) => sum + (a.data?.approved_amount || 0), 0)
              .toLocaleString()}`}
            icon={<TrendingUp className="w-8 h-8 text-purple-600" />}
            trend="+15% growth"
          />
        </motion.div>

        {/* Applications List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <h2 className="text-2xl font-bold mb-4">Your Applications</h2>
          {applications.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-xl p-12 text-center">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-xl font-semibold mb-2">No applications yet</h3>
              <p className="text-gray-600 dark:text-gray-300 mb-6">
                Start your loan journey by chatting with our AI assistant
              </p>
              <button
                onClick={() => router.push('/chat')}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold"
              >
                Start New Application
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {applications.map((app, index) => (
                <ApplicationCard key={app._id || index} application={app} />
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}

function QuickActionCard({ icon, title, description, onClick, color }) {
  return (
    <button
      onClick={onClick}
      className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow hover:shadow-lg transition-all group"
    >
      <div className={`${color} w-12 h-12 rounded-lg flex items-center justify-center mb-4 text-white group-hover:scale-110 transition-transform`}>
        {icon}
      </div>
      <h3 className="font-semibold mb-1">{title}</h3>
      <p className="text-sm text-gray-600 dark:text-gray-300">{description}</p>
    </button>
  )
}

function StatCard({ title, value, icon, trend }) {
  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">{title}</p>
          <p className="text-3xl font-bold">{value}</p>
        </div>
        {icon}
      </div>
      <p className="text-sm text-green-600 dark:text-green-400">{trend}</p>
    </div>
  )
}

function ApplicationCard({ application }) {
  const getStatusColor = (state) => {
    const colors = {
      INIT: 'bg-gray-100 text-gray-800',
      SALES: 'bg-blue-100 text-blue-800',
      KYC: 'bg-yellow-100 text-yellow-800',
      CREDIT: 'bg-purple-100 text-purple-800',
      DOCUMENTS: 'bg-orange-100 text-orange-800',
      OFFER: 'bg-indigo-100 text-indigo-800',
      ACCEPTANCE: 'bg-pink-100 text-pink-800',
      SANCTION: 'bg-teal-100 text-teal-800',
      COMPLETE: 'bg-green-100 text-green-800',
    }
    return colors[state] || colors.INIT
  }

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-semibold text-lg mb-1">
            {application.data?.loan_type || 'Loan Application'}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Amount: ₹{application.data?.loan_amount?.toLocaleString() || 'N/A'}
          </p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(application.state)}`}>
          {application.state}
        </span>
      </div>
      <div className="flex gap-4 text-sm text-gray-600 dark:text-gray-300">
        <div>
          <span className="font-medium">Created:</span>{' '}
          {new Date(application.createdAt).toLocaleDateString()}
        </div>
        {application.data?.tenure && (
          <div>
            <span className="font-medium">Tenure:</span> {application.data.tenure} months
          </div>
        )}
        {application.riskLevel && (
          <div>
            <span className="font-medium">Risk:</span> {application.riskLevel}
          </div>
        )}
      </div>
    </div>
  )
}
