'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight, Shield, Zap, Brain, CheckCircle } from 'lucide-react'

export default function Home() {
  const { data: session, status } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (status === 'authenticated') {
      router.push('/dashboard')
    }
  }, [status, router])

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-4xl mx-auto"
        >
          <h1 className="text-6xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600">
            AI-Powered Loan Processing
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8">
            Experience the future of banking with our intelligent agent system.
            Get loan approvals in minutes, not days.
          </p>
          <div className="flex gap-4 justify-center">
            <button
              onClick={() => router.push('/auth/signin')}
              className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold flex items-center gap-2 transition-all transform hover:scale-105"
            >
              Get Started <ArrowRight className="w-5 h-5" />
            </button>
            <button
              onClick={() => router.push('/chat')}
              className="px-8 py-4 border-2 border-blue-600 text-blue-600 hover:bg-blue-50 dark:hover:bg-gray-800 rounded-lg font-semibold transition-all"
            >
              Try Demo
            </button>
          </div>
        </motion.div>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="grid md:grid-cols-3 gap-8 mt-20"
        >
          <FeatureCard
            icon={<Brain className="w-10 h-10 text-blue-600" />}
            title="AI Agents"
            description="Intelligent agents handle sales, KYC, underwriting, and more"
          />
          <FeatureCard
            icon={<Zap className="w-10 h-10 text-purple-600" />}
            title="Instant Processing"
            description="Get loan decisions in minutes with automated workflows"
          />
          <FeatureCard
            icon={<Shield className="w-10 h-10 text-green-600" />}
            title="Secure & Compliant"
            description="Bank-grade security with full audit trails and compliance"
          />
        </motion.div>

        {/* Process Steps */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-20"
        >
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid md:grid-cols-4 gap-6">
            <ProcessStep number="1" title="Chat" description="Tell us what you need" />
            <ProcessStep number="2" title="Verify" description="Quick KYC process" />
            <ProcessStep number="3" title="Assess" description="AI-powered credit check" />
            <ProcessStep number="4" title="Approve" description="Get your sanction letter" />
          </div>
        </motion.div>
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow">
      <div className="mb-4">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-gray-600 dark:text-gray-300">{description}</p>
    </div>
  )
}

function ProcessStep({ number, title, description }) {
  return (
    <div className="flex flex-col items-center text-center">
      <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mb-4">
        {number}
      </div>
      <h4 className="font-semibold text-lg mb-2">{title}</h4>
      <p className="text-gray-600 dark:text-gray-300 text-sm">{description}</p>
    </div>
  )
}
