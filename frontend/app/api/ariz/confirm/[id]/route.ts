import { NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(
  _req: Request,
  { params }: { params: { id: string } }
) {
  const resp = await fetch(`${BACKEND}/api/ariz/confirm/${params.id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}
