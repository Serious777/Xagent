export async function POST(req: Request) {
  const { messages } = await req.json();

  const response = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
  });

  // 读取后端 SSE 流，转换为 Vercel AI SDK 需要的格式
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  const stream = new ReadableStream({
    async start(controller) {
      const reader = response.body!.getReader();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              if (data === '[DONE]') {
                controller.enqueue(encoder.encode('0:'));
                controller.close();
                return;
              }
              try {
                const parsed = JSON.parse(data);
                if (parsed.type === 'content' && parsed.text) {
                  // 转换为 Vercel AI SDK 文本流格式: "0:<text>"
                  controller.enqueue(encoder.encode(`0:${JSON.stringify(parsed.text)}\n`));
                } else if (parsed.type === 'tool_result') {
                  // 工具调用结果作为文本显示
                  const toolText = `\n\n**调用工具: ${parsed.tool}**\n\`\`\`json\n${JSON.stringify(parsed.result, null, 2)}\n\`\`\`\n`;
                  controller.enqueue(encoder.encode(`0:${JSON.stringify(toolText)}\n`));
                }
              } catch (e) {
                // 忽略解析错误
              }
            }
          }
        }
        controller.close();
      } catch (e) {
        controller.error(e);
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'X-Vercel-AI-Data-Stream': 'v1',
    },
  });
}
