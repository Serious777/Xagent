'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MessageProps {
  message: {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
  };
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg p-4 ${
          isUser
            ? 'bg-blue-500 text-white'
            : 'bg-white border text-gray-800'
        }`}
      >
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }) {
                if (inline) {
                  return (
                    <code className="bg-gray-100 px-1 rounded text-sm" {...props}>
                      {children}
                    </code>
                  );
                }
                const match = /language-(\w+)/.exec(className || '');
                return (
                  <div className="my-2">
                    <SyntaxHighlighter
                      style={oneDark}
                      language={match ? match[1] : 'text'}
                      PreTag="div"
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  </div>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
