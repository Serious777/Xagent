import http from 'http';

export async function POST(
  req: Request,
  { params }: { params: { id: string } }
) {
  const convId = params.id;

  return new Promise<Response>((resolve, reject) => {
    const options = {
      hostname: '127.0.0.1',
      port: 8000,
      path: `/api/ariz/confirm/${convId}`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const proxyReq = http.request(options, (proxyRes) => {
      let data = '';
      proxyRes.on('data', (chunk) => (data += chunk));
      proxyRes.on('end', () => {
        resolve(
          new Response(data, {
            status: proxyRes.statusCode,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      });
    });

    proxyReq.on('error', (err) => reject(err));
    proxyReq.end();
  });
}
