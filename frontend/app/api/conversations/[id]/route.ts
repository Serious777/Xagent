import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export async function DELETE(_req: NextRequest, { params }: { params: { id: string } }) {
  const resp = await fetch(`${BACKEND}/api/conversations/${params.id}`, { method: 'DELETE' });
  const data = await resp.json();
  return NextResponse.json(data);
}

export async function PATCH(req: NextRequest, { params }: { params: { id: string } }) {
  const body = await req.json();
  const resp = await fetch(`${BACKEND}/api/conversations/${params.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  return NextResponse.json(data);
}
