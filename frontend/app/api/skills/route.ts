import { NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export async function GET() {
  const resp = await fetch(`${BACKEND}/api/skills`);
  const data = await resp.json();
  return NextResponse.json(data);
}
