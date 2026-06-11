import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  const resp = await fetch(`${BACKEND}/api/conversations/${params.id}/messages`);
  const data = await resp.json();
  return NextResponse.json(data);
}
