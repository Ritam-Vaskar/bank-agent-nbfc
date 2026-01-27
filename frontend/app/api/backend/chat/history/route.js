import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'

export async function GET(request) {
  try {
    const session = await getServerSession()
    
    if (!session) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    // Forward request to backend
    const backendUrl = process.env.BACKEND_URL || 'http://backend:5000'
    const response = await fetch(`${backendUrl}/api/chat/history`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.accessToken}`,
      },
    })

    const data = await response.json()
    
    if (!response.ok) {
      return NextResponse.json(
        { error: data.message || 'Failed to fetch history' },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Chat history API error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
