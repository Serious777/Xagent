import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export async function GET() {
  const resp = await fetch(`${BACKEND}/api/conversations`);
  const data = await resp.json();
  return NextResponse.json(data);
}

export async function POST(req: NextRequest) {
  const resp = await fetch(`${BACKEND}/api/conversations`, { method: 'POST' });
  const data = await resp.json();
  return NextResponse.json(data);
}
