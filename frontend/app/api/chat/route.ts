import http from 'http';

export async function POST(req: Request) {
  const { messages, conversation_id } = await req.json();

  return new Promise<Response>((resolve, reject) => {
    const postData = JSON.stringify({ messages, conversation_id });

    const options = {
      hostname: '127.0.0.1',
      port: 8000,
      path: '/api/chat',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
      },
    };

    const proxyReq = http.request(options, (proxyRes) => {
      const stream = new ReadableStream({
        start(controller) {
          proxyRes.on('data', (chunk) => controller.enqueue(chunk));
          proxyRes.on('end', () => controller.close());
          proxyRes.on('error', (err) => controller.error(err));
        },
      });
      resolve(new Response(stream, {
        headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Vercel-AI-Data-Stream': 'v1' },
      }));
    });

    proxyReq.on('error', (err) => reject(err));
    proxyReq.write(postData);
    proxyReq.end();
  });
}
