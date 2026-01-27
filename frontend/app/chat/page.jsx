'use client'

import { useState, useEffect, useRef } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Loader2, Home } from 'lucide-react'
import Navbar from '@/components/Navbar'
import axios from 'axios'

export default function Chat() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loanId, setLoanId] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    // Add welcome message
    setMessages([
      {
        role: 'assistant',
        content:
          "👋 Hello! I'm your AI loan assistant. I'll help you through the loan application process. To get started, tell me what kind of loan you're looking for.",
        timestamp: new Date(),
      },
    ])
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await axios.post('/api/backend/chat/message', {
        message: input,
        loanId: loanId,
        userId: session?.user?.id || 'guest',
      })

      const { reply, loanId: newLoanId, state, completed } = response.data

      if (newLoanId && !loanId) {
        setLoanId(newLoanId)
      }

      const assistantMessage = {
        role: 'assistant',
        content: reply,
        state: state,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])

      // If loan is completed, show celebration
      if (completed || state === 'COMPLETE') {
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content:
                '🎉 Congratulations! Your loan has been approved and sanctioned. You can view your sanction letter in the dashboard.',
              timestamp: new Date(),
            },
          ])
        }, 1000)
      }
    } catch (error) {
      console.error('Chat error:', error)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '❌ Sorry, something went wrong. Please try again.',
          timestamp: new Date(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar />

      <div className="flex-1 container mx-auto px-4 py-6 flex flex-col max-w-4xl">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto space-y-4 mb-4">
          <AnimatePresence>
            {messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-3"
            >
              <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-2xl rounded-tl-sm p-4 max-w-[80%] shadow">
                <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              className="flex-1 px-4 py-3 bg-gray-50 dark:bg-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser ? 'bg-green-600' : 'bg-blue-600'
        }`}
      >
        {isUser ? (
          <User className="w-6 h-6 text-white" />
        ) : (
          <Bot className="w-6 h-6 text-white" />
        )}
      </div>

      <div
        className={`rounded-2xl p-4 max-w-[80%] shadow ${
          isUser
            ? 'bg-green-600 text-white rounded-tr-sm'
            : 'bg-white dark:bg-gray-800 rounded-tl-sm'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.state && (
          <p className="text-xs mt-2 opacity-70">Stage: {message.state}</p>
        )}
        <p className={`text-xs mt-2 ${isUser ? 'text-white/70' : 'text-gray-500'}`}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </motion.div>
  )
}
