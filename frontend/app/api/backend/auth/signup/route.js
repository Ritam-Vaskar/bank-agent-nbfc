import { NextResponse } from 'next/server'

export async function POST(request) {
  try {
    const body = await request.json()
    
    // Forward request to backend - MUST use Docker service name
    const backendUrl = process.env.BACKEND_URL || 'http://backend:5000'
    console.log('[SIGNUP] Using backend URL:', backendUrl)
    
    const response = await fetch(`${backendUrl}/api/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()

    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('Signup API error:', error)
    return NextResponse.json(
      { success: false, message: 'Failed to connect to backend' },
      { status: 500 }
    )
  }
}
