const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(req: Request) {
  const { messages, conversation_id } = await req.json();

  const resp = await fetch(`${BACKEND_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, conversation_id }),
  });

  if (!resp.ok) {
    return new Response(JSON.stringify({ error: `Backend error: ${resp.status}` }), {
      status: resp.status,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // 透传流式响应
  return new Response(resp.body, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'X-Vercel-AI-Data-Stream': 'v1',
    },
  });
}
