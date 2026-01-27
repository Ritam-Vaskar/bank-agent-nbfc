import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'

export async function POST(request) {
  try {
    const session = await getServerSession()
    
    const body = await request.json()
    
    // Forward request to backend
    const backendUrl = process.env.BACKEND_URL || 'http://backend:5000'
    const response = await fetch(`${backendUrl}/api/chat/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': session?.accessToken ? `Bearer ${session.accessToken}` : '',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    
    if (!response.ok) {
      return NextResponse.json(
        { error: data.message || 'Failed to send message' },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
